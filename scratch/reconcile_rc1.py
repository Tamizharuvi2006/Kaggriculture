import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, time, kaggle_environments
import submission_rc1_ev_dispatcher as rc1

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

expected_scores = {
    "RicardoLópez (1052 Elo)": 31598,
    "JZ (1000+ Elo)": 60931,
    "ayman elamin (1000+ Elo)": 64810,
    "Soumi Ghosh": 35127,
    "arao": 44684,
}

print("=" * 85)
print("     EXACT REPRODUCIBILITY VERIFICATION: RC1 OFFICIAL ENTRYPOINT     ")
print("=" * 85)

actual_scores = {}

for r_name, cand_seat, opp_name in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    with open(path) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
    env.reset()
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs = env.state[cand_seat].observation
        # Call official rc1.agent(obs)
        act = rc1.agent(obs)
        joint = [None, None]
        joint[cand_seat] = act
        joint[1 - cand_seat] = opp_actions[s]
        env.step(joint)
        
    score = env.state[cand_seat].reward
    actual_scores[opp_name] = score
    exp = expected_scores[opp_name]
    diff = score - exp
    status = "EXACT MATCH [PASS]" if diff == 0 else f"MISMATCH ({diff:+,.0f})"
    print(f"  {opp_name:<26}: Actual ${score:>7,.0f} | Expected ${exp:>7,.0f} -> {status}")

total_act = sum(actual_scores.values())
total_exp = sum(expected_scores.values())
print("-" * 85)
print(f"  TOTAL REVENUE: Actual ${total_act:>8,.0f} | Expected ${total_exp:>8,.0f} -> Diff: ${total_act - total_exp:+,.0f}")
print("=" * 85)
