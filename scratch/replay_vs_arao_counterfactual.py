import sys
import os
sys.path.insert(0, r"D:\kaggriculture")

import json
import kaggle_environments
import submission_challenger_exp208_clean as challenger

# Load arao's exact actions from the replay
replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed") # 1624303674

print(f"Loaded replay with seed {seed}, total steps {len(steps)}")

# Extract arao's actions (arao was Player 0)
arao_actions = [frame[0].get("action") for frame in steps]

# Test current policy on Seat 1 vs arao's recorded actions
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

step_num = 0
while not env.done:
    obs1 = env.state[1].observation
    act1 = challenger.agent(obs1)
    
    act0 = arao_actions[step_num] if step_num < len(arao_actions) else {"farmer": ["PASS"], "hands": [], "market": []}
    
    env.step([act0, act1])
    step_num += 1

final_arao = env.state[0].reward
final_hero = env.state[1].reward

print(f"\n=========================================================================================")
print(f"     EXACT REPLAY MATCH ON SEED {seed}                                                  ")
print(f"=========================================================================================")
print(f"Original Live Match Result : arao = $55,146 | Hero = $40,642 (Delta: -14,504)")
print(f"Current Clean Candidate    : arao = ${final_arao:,.0f} | Hero = ${final_hero:,.0f} (Delta: {final_hero - final_arao:+,.0f})")
