import os, json

path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"

with open(path_soumi) as f: rep_soumi = json.load(f)
with open(path_arao) as f: rep_arao = json.load(f)

print("=" * 85)
print("MARKET INVENTORY TRAJECTORY ON DAYS 14 TO 21: SOUMI vs ARAO")
print("=" * 85)
print(f"{'DAY':<4} | {'HOUR':<4} | {'SOUMI INV':>10} | {'SOUMI dI':>9} | {'ARAO INV':>9} | {'ARAO dI':>8}")
print("-" * 85)

prev_s_inv = None
prev_a_inv = None

for s in range(14 * 24, 21 * 24):
    day = s // 24
    hour = s % 24
    
    inv_s = rep_soumi["steps"][s][1]["observation"]["market"]["inventory"].get("STRAWBERRY", 10000)
    inv_a = rep_arao["steps"][s][1]["observation"]["market"]["inventory"].get("STRAWBERRY", 10000)
    
    delta_s = (inv_s - prev_s_inv) if prev_s_inv is not None else 0
    delta_a = (inv_a - prev_a_inv) if prev_a_inv is not None else 0
    
    prev_s_inv = inv_s
    prev_a_inv = inv_a
    
    # Print every 6 hours or when significant delta occurs
    if hour in (0, 6, 12, 18) or abs(delta_s) >= 5 or abs(delta_a) >= 5:
        print(f"D{day:02d} | H{hour:02d} | {inv_s:>10,} | {delta_s:>+9} | {inv_a:>9,} | {delta_a:>+8}")

print("=" * 85)
