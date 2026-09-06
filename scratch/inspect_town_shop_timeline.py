import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(replay_path) as f:
    rep = json.load(f)

steps = rep["steps"]

print("=" * 80)
print("TOWN SHOP UNLOCK TIMELINE (SOUMI GHOSH EPISODE):")
print("=" * 80)

prev_shops = []
for s_idx in range(0, len(steps), 24):
    day = s_idx // 24
    obs = steps[s_idx][0]["observation"]
    town = obs.get("town", {})
    unlocked = town.get("unlocked_shops", [])
    if unlocked != prev_shops:
        prev_shops = list(unlocked)
        # Count strawberry shops
        from kaggle_environments.envs.kaggriculture.kaggriculture import SHOPS
        straw_shops = [s for s in unlocked if "STRAWBERRY" in SHOPS.get(s, [])]
        print(f"Day {day:02d}: Total Shops: {len(unlocked)} | Strawberry Shops: {len(straw_shops)} -> {straw_shops}")
