import sys
sys.path.insert(0, r"D:\kaggriculture")

import json
import kaggle_environments
import submission_challenger_exp208_clean as challenger

with open(r"D:\kaggriculture\topreply\loss\104499847.json", "r", encoding="utf-8") as f:
    replay = json.load(f)

seed = replay.get("info", {}).get("seed")
steps = replay.get("steps", [])
opp_actions = [frame[1].get("action") for frame in steps[1:]] # Crop Dusta is idx 1

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

baseline_land = []
for s in range(len(opp_actions)):
    if env.done: break
    obs_cand = env.state[0].observation
    act_cand = challenger.agent(obs_cand)
    act_opp = opp_actions[s]
    
    mkt = act_cand.get("market") or []
    for o in mkt:
        if isinstance(o, (list, tuple)) and o and o[0] == "BUY_LAND":
            baseline_land.append((s, s//24, s%24, o, env.state[0].observation.get("farms")[0].get("money")))
            
    env.step([act_cand, act_opp])

print(f"Baseline Final Reward vs Crop Dusta: ${env.state[0].reward:,.0f} vs Crop Dusta: ${env.state[1].reward:,.0f}")
print("Baseline Land Purchases:")
for l in baseline_land:
    print(f"  Step {l[0]} (Day {l[1]} H{l[2]}): {l[3]} with Money=${l[4]:,.0f}")
