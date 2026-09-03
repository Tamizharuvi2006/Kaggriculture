import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

for s in [0, 1, 2, 50, 100]:
    obs1 = steps[s][1].get("observation", {})
    print(f"Step {s} observation keys in live replay: {list(obs1.keys())}")
    print(f"  obs1.get('step') = {obs1.get('step')}")
    print(f"  obs1.get('day') = {obs1.get('day')}, obs1.get('hour') = {obs1.get('hour')}")
