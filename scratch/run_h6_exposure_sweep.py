import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

def count_opp_straw(obs):
    farms = obs.farms
    player = obs.player
    if len(farms) < 2: return 0
    opp = farms[1 - player]
    return sum(1 for row in opp.tiles for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")

def run_game_with_quota(seed=None, replay_file=None, seat=1, quota_rule="baseline"):
    if replay_file:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", replay_file)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
    else:
        steps = range(721)
        opp_actions = None
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    # Store and patch _crop_plan
    orig_crop_plan = rc2_mod._crop_plan
    
    opp_straw_at_11 = 0
    
    for step in range(len(steps) - 1):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        
        if day == 11 and hour == 0:
            opp_straw_at_11 = count_opp_straw(obs)
            
        if quota_rule != "baseline" and day >= 11:
            # Apply exposure-aware quota
            opp_straw = count_opp_straw(obs)
            def patched_crop_plan(d):
                p = orig_crop_plan(d)
                if opp_straw > 8:
                    # Safe quota: 26 - opp_straw, capped at min 10
                    if quota_rule == "adaptive_26":
                        max_s = max(10, 26 - opp_straw)
                    elif quota_rule == "cap_15":
                        max_s = 15
                    elif quota_rule == "cap_12":
                        max_s = 12
                    else:
                        max_s = 26
                        
                    s_count = 0
                    new_p = {}
                    for pos, c in p.items():
                        if c == "STRAWBERRY":
                            if s_count < max_s:
                                new_p[pos] = "STRAWBERRY"
                                s_count += 1
                            else:
                                new_p[pos] = "CARROT" # Divert surplus to Carrot!
                        else:
                            new_p[pos] = c
                    return new_p
                return p
            rc2_mod._crop_plan = patched_crop_plan
            
        try:
            if replay_file:
                act0 = opp_actions[step] if seat == 1 else rc2_mod.agent(env.state[0].observation)
                act1 = rc2_mod.agent(env.state[1].observation) if seat == 1 else opp_actions[step]
            else:
                act0 = rc2_mod.agent(env.state[0].observation)
                act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        env.step([act0, act1])
        
    final_score = env.state[seat].observation.farms[seat].money
    final_p_straw = env.state[seat].observation.market.prices.get("STRAWBERRY", 0)
    return {
        "score": final_score,
        "final_p_straw": final_p_straw,
        "opp_straw_at_11": opp_straw_at_11
    }

print("=" * 105)
print("H6 CANDIDATE EVALUATION: OPPONENT-EXPOSURE-AWARE STRAWBERRY ALLOCATION")
print("=" * 105)

test_targets = [
    ("Soumi Ghosh S1 (Worst Floor)", "episode-104388418-replay.json", None, 1),
    ("RicardoLópez S1 (Grandmaster)", "episode-104475527-replay.json", None, 1),
    ("Seed 628719714 S1 (High Ceiling)", None, 628719714, 1),
]

for label, rep_file, seed_val, seat_val in test_targets:
    print(f"\nTarget: {label}")
    # 1. Baseline RC2
    b_res = run_game_with_quota(seed=seed_val, replay_file=rep_file, seat=seat_val, quota_rule="baseline")
    # 2. Adaptive Rule: max(10, 26 - opp_straw)
    a_res = run_game_with_quota(seed=seed_val, replay_file=rep_file, seat=seat_val, quota_rule="adaptive_26")
    # 3. Fixed Cap 15 when opp > 8
    c_res = run_game_with_quota(seed=seed_val, replay_file=rep_file, seat=seat_val, quota_rule="cap_15")
    
    print(f"  Opponent Strawberries at Day 11: {b_res['opp_straw_at_11']}")
    print(f"  Baseline RC2:         ${b_res['score']:>8,.0f} | Final Strawberry Price: ${b_res['final_p_straw']:.1f}")
    print(f"  Adaptive (26 - opp):  ${a_res['score']:>8,.0f} | Final Strawberry Price: ${a_res['final_p_straw']:.1f} | Delta: ${a_res['score'] - b_res['score']:>+7,.0f}")
    print(f"  Cap 15:               ${c_res['score']:>8,.0f} | Final Strawberry Price: ${c_res['final_p_straw']:.1f} | Delta: ${c_res['score'] - b_res['score']:>+7,.0f}")

print("\n" + "=" * 105)
print("SWEEP COMPLETE.")
print("=" * 105)
