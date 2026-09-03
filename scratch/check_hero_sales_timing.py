import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

print("Hero Wool and Milk sales in Episode 104379472:")
for s in range(len(steps)):
    frame = steps[s]
    act1 = frame[1].get("action", {})
    market1 = act1.get("market", [])
    prices = frame[0].get("observation", {}).get("market", {}).get("prices", {})
    
    for m in market1:
        if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL" and m[1] in ("WOOL", "MILK"):
            day = s // 24
            hour = s % 24
            print(f"Step {s:3d} (D{day:2d} h{hour:2d}): Sold {m[2]} {m[1]} at price ${prices.get(m[1])}")
