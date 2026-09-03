import json
import kaggle_environments
import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
seed = replay.get("info", {}).get("seed")

arao_actions = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done: break
    obs1 = env.state[1].observation
    act1 = challenger.agent(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])

r0 = env.state[0].reward
r1 = env.state[1].reward

print("=========================================================================================")
print(f"     AFTER STEP FIX: CLEAN CANDIDATE AGENT DIRECT RUN VS ARAO                           ")
print("=========================================================================================")
print(f"Live Match Result: arao = $55,146 | Hero = $40,642 (Margin: -14,504)")
print(f"Clean Fixed Agent: arao = ${r0:,.0f} | Hero = ${r1:,.0f} (Margin: {r1 - r0:+,.0f})")
