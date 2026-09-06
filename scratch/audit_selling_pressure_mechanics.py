import json

path_soumi = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
path_arao = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"

with open(path_soumi) as f: rep_soumi = json.load(f)
with open(path_arao) as f: rep_arao = json.load(f)

print("=" * 95)
print(f"{'DAY':<4} | {'SOUMI OPP SOLD':>15} | {'SOUMI MKT INV':>14} | {'SOUMI PRICE':>12} | {'ARAO OPP SOLD':>14} | {'ARAO MKT INV':>13} | {'ARAO PRICE':>11}")
print("-" * 95)

for day in range(11, 28):
    # Step range for day: day * 24 to (day + 1) * 24
    s_start = day * 24
    s_end = (day + 1) * 24
    
    # Soumi sales (Seat 0 was Soumi)
    soumi_sales = 0
    for s in range(s_start, min(s_end, len(rep_soumi["steps"])-1)):
        act = rep_soumi["steps"][s+1][0].get("action", {})
        if isinstance(act, dict):
            for o in act.get("market", []):
                if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                    soumi_sales += o[2]
    soumi_inv = rep_soumi["steps"][s_start][1]["observation"]["market"]["inventory"].get("STRAWBERRY", 0)
    soumi_p = rep_soumi["steps"][s_start][1]["observation"]["market"]["prices"].get("STRAWBERRY", 0)
    
    # Arao sales (Seat 0 was Arao)
    arao_sales = 0
    for s in range(s_start, min(s_end, len(rep_arao["steps"])-1)):
        act = rep_arao["steps"][s+1][0].get("action", {})
        if isinstance(act, dict):
            for o in act.get("market", []):
                if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                    arao_sales += o[2]
    arao_inv = rep_arao["steps"][s_start][1]["observation"]["market"]["inventory"].get("STRAWBERRY", 0)
    arao_p = rep_arao["steps"][s_start][1]["observation"]["market"]["prices"].get("STRAWBERRY", 0)
    
    print(f"D{day:02d} | {soumi_sales:>15} | {soumi_inv:>14,} | ${soumi_p:>11.1f} | {arao_sales:>14} | {arao_inv:>13,} | ${arao_p:>10.1f}")

print("=" * 95)
