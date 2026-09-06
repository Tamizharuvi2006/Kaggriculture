import json

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
seat = 0

for s in range(1, len(steps)):
    step = steps[s]
    act = step[seat].get("action", {})
    obs = step[seat]["observation"]
    day = obs["day"]
    hour = obs["hour"]
    market = act.get("market", [])
    for o in market:
        if o and o[0] in ("BUY_PRODUCT", "BUY_SEED") and o[1] == "WHEAT":
            print(f"Day {day:02d} H{hour:02d}: {o}")
