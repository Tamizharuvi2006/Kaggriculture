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

def agent_smart_feed(obs):
    act = challenger.agent(obs)
    if not isinstance(act, dict): return act
    step = int(obs.get("step") if obs.get("step") is not None else int(obs.get("day", 0))*24 + int(obs.get("hour", 0)))
    day = step // 24
    if day >= 28:
        clean_mkt = []
        for m in act.get("market", []):
            if isinstance(m, list) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT":
                continue
            clean_mkt.append(m)
        act["market"] = clean_mkt
    return act

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done: break
    obs1 = env.state[1].observation
    act1 = agent_smart_feed(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])
    
    # check status
    status1 = env.state[1].status
    if status1 != "ACTIVE" and not env.done:
        print(f"Step {s} Hero status changed to {status1}! Info: {env.state[1].info}")
        break

print(f"Final state: P0 status={env.state[0].status}, reward={env.state[0].reward} | P1 status={env.state[1].status}, reward={env.state[1].reward}")
