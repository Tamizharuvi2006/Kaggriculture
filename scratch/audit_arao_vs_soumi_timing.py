import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments

replays = [
    ("episode-104388418-replay.json", "Soumi Ghosh (S1: +19.1k)", 1),
    ("episode-104379472-replay.json", "arao (S1: -13.7k)", 1),
]

for r_name, label, seat in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    with open(path) as f: rep = json.load(f)
    steps = rep["steps"]
    
    print("=" * 80)
    print(f"FORENSIC TIMING & MECHANISM AUDIT: {label}")
    print("=" * 80)
    
    # Inspect step-by-step from Day 10 Hour 18 to Day 13 Hour 0
    # Steps: 240 to 312
    for s in range(10 * 24 + 18, 13 * 24):
        day = s // 24
        hour = s % 24
        obs = steps[s][seat]["observation"]
        opp_farm = obs["farms"][1 - seat]
        our_farm = obs["farms"][seat]
        
        opp_straw = sum(1 for r in opp_farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        our_straw = sum(1 for r in our_farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        
        p_straw = obs["market"]["prices"].get("STRAWBERRY", 0)
        inv_straw = obs["market"]["inventory"].get("STRAWBERRY", 0)
        
        # Check if opponent sold strawberries
        opp_act = steps[s+1][1 - seat].get("action") if s + 1 < len(steps) else {}
        opp_straw_sells = 0
        if isinstance(opp_act, dict):
            for o in opp_act.get("market", []):
                if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                    opp_straw_sells += o[2]
                    
        if hour in (0, 6, 12, 18) or opp_straw_sells > 0:
            print(f"Day {day:02d} Hr {hour:02d} | Opp Straw Bushes: {opp_straw:>2} | Our Straw Bushes: {our_straw:>2} | Opp Sold: {opp_straw_sells:>2} | Mkt Inv: {inv_straw:>5,} | Price: ${p_straw:.1f}")

    # Also inspect final market state on Day 28
    last_obs = steps[-2][seat]["observation"]
    print(f"\nFinal Day 29 Strawberry Market State: Inventory = {last_obs['market']['inventory'].get('STRAWBERRY', 0):,} | Price = ${last_obs['market']['prices'].get('STRAWBERRY', 0):.1f}")
