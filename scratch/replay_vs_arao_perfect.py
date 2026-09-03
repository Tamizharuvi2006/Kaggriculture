import json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

arao_actions = [frame[0].get("action") for frame in steps[1:]]
hero_recorded_actions = [frame[1].get("action") for frame in steps[1:]]

# 1. First recreate EXACT match using recorded actions
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

for s in range(len(arao_actions)):
    if env.done:
        break
    act0 = arao_actions[s]
    act1 = hero_recorded_actions[s]
    env.step([act0, act1])

print(f"Exact Recorded Replay Check: P0 (arao) = ${env.state[0].reward:,.0f} | P1 (Hero) = ${env.state[1].reward:,.0f}")
