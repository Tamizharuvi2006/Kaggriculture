import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import kaggle_environments
import submission_challenger_exp208_clean as challenger

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

for s in range(5):
    obs0 = env.state[0].observation
    obs1 = env.state[1].observation
    
    act0_recorded = steps[s][0].get("action")
    act1_recorded = steps[s][1].get("action")
    
    act1_agent = challenger.agent(obs1)
    
    print(f"Step {s}:")
    print(f"  act0_recorded: {act0_recorded}")
    print(f"  act1_recorded: {act1_recorded}")
    print(f"  act1_agent   : {act1_agent}")
    print(f"  Matches recorded? {act1_agent == act1_recorded}")
    
    env.step([act0_recorded, act1_recorded])
