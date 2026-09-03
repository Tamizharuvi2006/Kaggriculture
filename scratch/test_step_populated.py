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

def agent_fixed(obs, configuration=None):
    try:
        step = int(obs.get("step") if obs.get("step") is not None else int(obs.get("day", 0))*24 + int(obs.get("hour", 0)))
        if isinstance(obs, dict):
            obs["step"] = step
        return challenger.agent(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done: break
    obs1 = env.state[1].observation
    act1 = agent_fixed(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])

r0 = env.state[0].reward
r1 = env.state[1].reward
print(f"Result with obs['step'] populated: arao=${r0:,.0f} | Hero=${r1:,.0f} (Margin: {r1 - r0:+,.0f})")
