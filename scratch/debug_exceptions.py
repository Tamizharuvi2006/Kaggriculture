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

exceptions = []

def agent_fixed_debug(obs, configuration=None):
    try:
        step = int(obs.get("step") if obs.get("step") is not None else int(obs.get("day", 0))*24 + int(obs.get("hour", 0)))
        if isinstance(obs, dict):
            obs["step"] = step
        return challenger.agent(obs)
    except Exception as e:
        exceptions.append((step, str(e)))
        return {"farmer": ["PASS"], "hands": [], "market": []}

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done: break
    obs1 = env.state[1].observation
    act1 = agent_fixed_debug(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])
    
    if env.state[1].status != "ACTIVE" and not env.done:
        print(f"Step {s} Hero failed! Status: {env.state[1].status}")
        break

print(f"Exceptions caught: {len(exceptions)}")
if exceptions:
    print(f"First exception: {exceptions[0]}")
