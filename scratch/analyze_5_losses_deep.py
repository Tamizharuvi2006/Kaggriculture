import json
import glob
from collections import defaultdict

files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")

print("=========================================================================================")
print(f"     DEEP ECONOMIC REVENUE & PRICE AUDIT ACROSS {len(files)} LIVE LOSS REPLAYS          ")
print("=========================================================================================")

for fpath in files:
    with open(fpath, "r", encoding="utf-8") as fp:
        replay = json.load(fp)
    
    info = replay.get("info", {})
    eid = info.get("EpisodeId")
    rewards = replay.get("rewards", [])
    agents = info.get("Agents", [])
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    hero_rew = rewards[hero_idx]
    opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    if not steps: continue
    
    hero_sales_units = defaultdict(int)
    opp_sales_units = defaultdict(int)
    hero_sales_revenue = defaultdict(float)
    opp_sales_revenue = defaultdict(float)
    
    # Trace step-by-step transactions
    for s in range(1, len(steps)):
        # Previous step market prices
        prev_obs = steps[s-1][0].get("observation", {})
        prices = prev_obs.get("market", {}).get("prices", {})
        
        # Actions taken in previous step that executed at this step
        frame = steps[s]
        act_hero = frame[hero_idx].get("action", {})
        act_opp = frame[opp_idx].get("action", {})
        
        # Hero market sales
        for order in act_hero.get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
                prod = order[1]
                qty = int(order[2])
                price = float(prices.get(prod, 0))
                hero_sales_units[prod] += qty
                hero_sales_revenue[prod] += qty * price
                
        # Opponent market sales
        for order in act_opp.get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
                prod = order[1]
                qty = int(order[2])
                price = float(prices.get(prod, 0))
                opp_sales_units[prod] += qty
                opp_sales_revenue[prod] += qty * price
                
    print(f"\n--- Episode {eid}: Hero ${hero_rew:,.0f} vs Opp ${opp_rew:,.0f} (Delta: {hero_rew - opp_rew:+,.0f}) ---")
    all_prods = sorted(set(list(hero_sales_units.keys()) + list(opp_sales_units.keys())))
    
    print(f"{'Product':>12} | {'Hero Units':>10} | {'Hero Rev ($)':>12} | {'Hero Avg P':>10} || {'Opp Units':>10} | {'Opp Rev ($)':>12} | {'Opp Avg P':>10}")
    print("-" * 95)
    for p in all_prods:
        hu = hero_sales_units[p]
        hr = hero_sales_revenue[p]
        hp = hr / max(1, hu)
        
        ou = opp_sales_units[p]
        ou_disp = ou if ou < 10000 else 9999 # cap display if bot passed 100000
        orr = opp_sales_revenue[p]
        op = orr / max(1, ou)
        print(f"{p:>12} | {hu:10d} | ${hr:11,.0f} | ${hp:9.1f} || {ou_disp:10d} | ${orr:11,.0f} | ${op:9.1f}")
