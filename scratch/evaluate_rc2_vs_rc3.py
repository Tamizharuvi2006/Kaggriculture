import sys
sys.path.insert(0, r"D:\kaggriculture")

import importlib, json, os, time, kaggle_environments

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

def run_agent_eval(mod_name, label):
    mod = importlib.import_module(mod_name)
    scores = {}
    plant_counts = {}
    
    print(f"\n--- Running Evaluation: {label} ({mod_name}) ---")
    for r_name, cand_seat, opp_name in replays:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
        
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
        env.reset()
        
        plants = {}
        for s in range(len(opp_actions)):
            if env.done: break
            obs = env.state[cand_seat].observation
            act = mod.agent(obs)
            
            # Count planting actions
            for h in act.get("hands", []) or []:
                if h and len(h) >= 2 and h[0] == "PLANT":
                    crop = h[1]
                    plants[crop] = plants.get(crop, 0) + 1
                    
            joint = [None, None]
            joint[cand_seat] = act
            joint[1 - cand_seat] = opp_actions[s]
            env.step(joint)
            
        score = env.state[cand_seat].reward
        scores[opp_name] = score
        plant_counts[opp_name] = plants
        plant_str = " ".join(f"{k}:{v}" for k, v in sorted(plants.items()))
        print(f"  {opp_name:<26}: ${score:,.0f} | Plants: {plant_str}")
        sys.stdout.flush()
        
    total = sum(scores.values())
    avg = total / len(scores)
    print(f"  => TOTAL: ${total:,.0f} | AVG: ${avg:,.0f}")
    return scores, plant_counts, total, avg

print("=" * 105)
print("     OFFICIAL HEAD-TO-HEAD BENCHMARK: RC2 CONTROL vs RC3 AMORTIZATION BRAIN     ")
print("=" * 105)

rc2_scores, rc2_plants, rc2_total, rc2_avg = run_agent_eval("submission_rc2_terminal_horizon", "RC2 Control")
rc3_scores, rc3_plants, rc3_total, rc3_avg = run_agent_eval("submission_rc3_economic_brain", "RC3 Amortization")

print("\n" + "=" * 105)
print("     COMPARATIVE HEAD-TO-HEAD LEADERBOARD     ")
print("=" * 105)
print(f"  {'Opponent / Seed':<26} | {'RC2 Control':>12} | {'RC3 Horizon':>12} | {'Net Lift':>12}")
print("-" * 105)
for _, _, opp_name in replays:
    s2 = rc2_scores[opp_name]
    s3 = rc3_scores[opp_name]
    lift = s3 - s2
    print(f"  {opp_name:<26} | ${s2:>10,.0f} | ${s3:>10,.0f} | ${lift:>+10,.0f}")
print("-" * 105)
total_lift = rc3_total - rc2_total
print(f"  {'TOTAL AGGREGATE':<26} | ${rc2_total:>10,.0f} | ${rc3_total:>10,.0f} | ${total_lift:>+10,.0f}")
print(f"  {'AVERAGE PER MATCH':<26} | ${rc2_avg:>10,.0f} | ${rc3_avg:>10,.0f} | ${rc3_avg - rc2_avg:>+10,.0f}")
print("=" * 105)
