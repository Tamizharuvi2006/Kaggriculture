import json
from collections import defaultdict

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

arao_units = defaultdict(int)
arao_rev = defaultdict(float)
hero_units = defaultdict(int)
hero_rev = defaultdict(float)

# Days 20 to 30 = step 480 to 720
for s in range(481, len(steps)):
    prices = steps[s-1][0].get("observation", {}).get("market", {}).get("prices", {})
    
    # arao (P0)
    act0 = steps[s][0].get("action", {})
    for m in act0.get("market", []):
        if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
            p = m[1]
            q = int(m[2])
            pr = float(prices.get(p, 0))
            arao_units[p] += q
            arao_rev[p] += q * pr
            
    # Hero (P1)
    act1 = steps[s][1].get("action", {})
    for m in act1.get("market", []):
        if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
            p = m[1]
            q = int(m[2])
            pr = float(prices.get(p, 0))
            hero_units[p] += q
            hero_rev[p] += q * pr

print("=========================================================================================")
print("     DAYS 20-30 SALES BREAKDOWN: ARAO VS HERO                                            ")
print("=========================================================================================")
all_prods = sorted(set(list(arao_units.keys()) + list(hero_units.keys())))
for p in all_prods:
    print(f"{p:>12}: ARAO Sold {arao_units[p]:5d} units (${arao_rev[p]:8,.0f}) || HERO Sold {hero_units[p]:5d} units (${hero_rev[p]:8,.0f})")
