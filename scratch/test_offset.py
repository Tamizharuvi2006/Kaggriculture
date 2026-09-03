import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

print("Step 0 action in steps[0]:", steps[0][0].get("action"))
print("Step 0 action in steps[1]:", steps[1][0].get("action"))
print("Step 1 action in steps[2]:", steps[2][0].get("action"))
