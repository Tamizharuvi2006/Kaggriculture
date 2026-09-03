import json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

arao_actions = [frame[0].get("action") for frame in steps[1:]]

import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission as sub_orig

# sub_orig is the original submission.py with _FIXED_SCHEDULE and v18
# Let's test sub_orig.agent vs arao_actions
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

for s in range(len(arao_actions)):
    if env.done: break
    obs1 = env.state[1].observation
    act1 = sub_orig.agent(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])

print(f"=========================================================================================")
print(f"     ORIGINAL SUBMISSION.PY (UNTOUCHED CONTROL) VS ARAO ON SEED {seed}                  ")
print("=========================================================================================")
print(f"Live Match Result: arao = $55,146 | Hero = $40,642")
print(f"submission.py    : arao = ${env.state[0].reward:,.0f} | Hero = ${env.state[1].reward:,.0f} (Margin: {env.state[1].reward - env.state[0].reward:+,.0f})")
