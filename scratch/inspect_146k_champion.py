import json

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    rep = json.load(f)

steps = rep["steps"]
seat = 0

daily_summary = {}

for s_idx in range(1, len(steps)):
    obs = steps[s_idx][seat]["observation"]
    act = steps[s_idx][seat].get("action") or {}
    day = obs.get("day", 0)
    farm = obs["farms"][seat]
    money = farm.get("money", 0)
    
    if day not in daily_summary:
        daily_summary[day] = {
            "end_money": money,
            "hires": 0,
            "buys": [],
            "sells": [],
            "land_buys": 0,
            "unlocked": len(farm.get("unlocked_quadrants", [])),
            "workers": len(farm.get("workers", [])),
        }
    
    daily_summary[day]["end_money"] = money
    daily_summary[day]["unlocked"] = len(farm.get("unlocked_quadrants", []))
    daily_summary[day]["workers"] = len(farm.get("workers", []))
    
    if isinstance(act, dict):
        for order in act.get("market", []):
            if not order: continue
            otype = order[0]
            if otype == "HIRE":
                daily_summary[day]["hires"] += 1
            elif otype == "BUY_LAND":
                daily_summary[day]["land_buys"] += 1
            elif otype in ("BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT"):
                daily_summary[day]["buys"].append((otype, order[1], order[2] if len(order) > 2 else 1))
            elif otype == "SELL":
                daily_summary[day]["sells"].append((order[1], order[2] if len(order) > 2 else 1))

print("="*110)
print(f"{'DAY':<4} | {'MONEY':>8} | {'WRK':>3} | {'HIRE':>4} | {'UNL':>3} | {'LAND':>4} | {'BUYS':<40} | {'SELLS':<30}")
print("="*110)
for day in sorted(daily_summary.keys()):
    d = daily_summary[day]
    buys_str = ", ".join(f"{b[1]}x{b[2]}" for b in d["buys"][:4])
    if len(d["buys"]) > 4: buys_str += f" (+{len(d['buys'])-4} more)"
    sells_str = ", ".join(f"{s[0]}x{s[1]}" for s in d["sells"][:3])
    if len(d["sells"]) > 3: sells_str += f" (+{len(d['sells'])-3} more)"
    print(f"D{day:<3} | ${d['end_money']:>7,.0f} | {d['workers']:>3} | {d['hires']:>4} | {d['unlocked']:>3} | {d['land_buys']:>4} | {buys_str:<40} | {sells_str:<30}")
