import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

hero_farmer_actions = set()
for s in range(len(steps)):
    frame = steps[s]
    act1 = frame[1].get("action", {})
    farmer_act = tuple(act1.get("farmer", []))
    hero_farmer_actions.add(farmer_act)

print(f"Total unique farmer actions taken by our hero across all 720 steps: {hero_farmer_actions}")
