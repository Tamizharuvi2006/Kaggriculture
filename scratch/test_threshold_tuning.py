import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

import submission_rc2_terminal_horizon as rc2_mod
import submission_h6_adaptive_allocation as h6_mod

# Test different threshold values: 14, 16, 18, 20
thresholds = [8, 14, 16, 18, 20]

print("=" * 95)
print("THRESHOLD SWEEP: CALIBRATING THE SATURATION TRIGGER (AVOIDING UNILATERAL CONCESSION)")
print("=" * 95)

# Target 1: Soumi Ghosh S1 (Worst Floor, Opp Straw = 25)
path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(path_soumi) as f: rep_soumi = json.load(f)
steps_soumi = rep_soumi["steps"]
tape_soumi = {s: (steps_soumi[s+1][0]["action"], None) for s in range(len(steps_soumi)-1)}

# Target 2: Ricardo S1 (1052 Elo, Opp Straw = 20)
path_ricardo = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(path_ricardo) as f: rep_ricardo = json.load(f)
steps_ricardo = rep_ricardo["steps"]
tape_ricardo = {s: (steps_ricardo[s+1][0]["action"], None) for s in range(len(steps_ricardo)-1)}

# Target 3: Live Head-to-Head Seed 628719714 (Part B, Opp Straw = 12)
seed_live = 628719714

def run_sim(threshold, target_type, seed_val=None, tape=None, max_steps=720):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": max_steps, "seed": seed_val})
    env.reset()
    
    orig_crop_plan = rc2_mod._crop_plan
    opp_straw_d11 = 0
    
    for step in range(max_steps):
        if env.done: break
        obs1 = env.state[1].observation
        day = obs1.day
        hour = obs1.hour
        
        if day == 11 and hour == 0:
            opp_farm = obs1.farms[0]
            opp_straw_d11 = sum(1 for r in opp_farm.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            
        if day >= 11 and opp_straw_d11 >= threshold:
            safe_quota = max(10, 26 - opp_straw_d11)
            def patched_crop_plan(d):
                p = orig_crop_plan(d)
                s_count = 0
                new_p = {}
                for pos, c in p.items():
                    if c == "STRAWBERRY":
                        if s_count < safe_quota:
                            new_p[pos] = "STRAWBERRY"
                            s_count += 1
                        else:
                            new_p[pos] = "CARROT"
                    else:
                        new_p[pos] = c
                return new_p
            rc2_mod._crop_plan = patched_crop_plan
            
        try:
            if tape:
                act0 = tape[step][0]
            else:
                act0 = rc2_mod.agent(env.state[0].observation)
            act1 = rc2_mod.agent(env.state[1].observation)
        finally:
            rc2_mod._crop_plan = orig_crop_plan
            
        env.step([act0, act1])
        
    return env.state[1].observation.farms[1].money, opp_straw_d11

print(f"{'THRESHOLD':<12} | {'SOUMI S1 (Opp=25)':>18} | {'RICARDO S1 (Opp=20)':>20} | {'LIVE H2H (Opp=12)':>20}")
print("-" * 95)

# Baseline (threshold = 999)
s_base, _ = run_sim(999, "replay", rep_soumi["info"]["seed"], tape_soumi, len(steps_soumi)-1)
r_base, _ = run_sim(999, "replay", rep_ricardo["info"]["seed"], tape_ricardo, len(steps_ricardo)-1)
l_base, _ = run_sim(999, "live", seed_live, None, 720)
print(f"{'Baseline RC2':<12} | ${s_base:>17,.0f} | ${r_base:>19,.0f} | ${l_base:>19,.0f}")

for t in thresholds:
    s_score, s_opp = run_sim(t, "replay", rep_soumi["info"]["seed"], tape_soumi, len(steps_soumi)-1)
    r_score, r_opp = run_sim(t, "replay", rep_ricardo["info"]["seed"], tape_ricardo, len(steps_ricardo)-1)
    l_score, l_opp = run_sim(t, "live", seed_live, None, 720)
    print(f"{'Opp >= ' + str(t):<12} | ${s_score:>17,.0f} | ${r_score:>19,.0f} | ${l_score:>19,.0f}")

print("=" * 95)
