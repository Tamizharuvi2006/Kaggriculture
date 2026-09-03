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
import submission_challenger_exp208_clean as challenger

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
    
    if s >= 715:
        m0 = env.state[0].observation["farms"][0]["money"]
        m1 = env.state[1].observation["farms"][1]["money"]
        r0 = env.state[0].reward
        r1 = env.state[1].reward
        st0 = env.state[0].status
        st1 = env.state[1].status
        print(f"Step {s}: Money P0=${m0:,.0f}, P1=${m1:,.0f} | Rewards: P0={r0}, P1={r1} | Status: P0={st0}, P1={st1}")
