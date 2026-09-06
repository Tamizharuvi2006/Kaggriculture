import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(replay_path) as f:
    rep = json.load(f)

steps = rep["steps"]

print("=" * 90)
print("FORENSIC TRACE: WHO FLOODED STRAWBERRIES ON DAYS 20 TO 26?")
print("=" * 90)

for step_idx in range(480, 620): # Days 20 to 26
    frame = steps[step_idx]
    day = step_idx // 24
    hour = step_idx % 24
    
    # Check player 0 (Soumi Ghosh) action
    act0 = frame[0].get("action", {})
    mkt0 = act0.get("market", []) if isinstance(act0, dict) else []
    
    # Check player 1 (Our bot RC2) action
    act1 = frame[1].get("action", {})
    mkt1 = act1.get("market", []) if isinstance(act1, dict) else []
    
    p0_straw_sales = [ord_item[2] for ord_item in mkt0 if len(ord_item) >= 3 and ord_item[0] == "SELL" and ord_item[1] == "STRAWBERRY"]
    p1_straw_sales = [ord_item[2] for ord_item in mkt1 if len(ord_item) >= 3 and ord_item[0] == "SELL" and ord_item[1] == "STRAWBERRY"]
    
    if p0_straw_sales or p1_straw_sales:
        print(f"Day {day:02d} Hr {hour:02d}: Soumi (P0) sold {sum(p0_straw_sales)} | Our Bot (P1) sold {sum(p1_straw_sales)}")
