import os, json
import numpy as np
import pandas as pd

replay_paths = [
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json",
    r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json",
]

step5b_dir = r"D:\kaggriculture\reports\step5b"
for root, dirs, files in os.walk(step5b_dir):
    for f in files:
        if f.endswith("-replay.json"):
            replay_paths.append(os.path.join(root, f))

print(f"Scanning {len(replay_paths)} full replays to extract opponent realization dataset...")

dataset_rows = []

for p in replay_paths:
    try:
        with open(p) as f: rep = json.load(f)
        steps = rep.get("steps", [])
        if len(steps) < 22 * 24: continue # need at least day 22
        
        # Determine Ground Truth: Did strawberry price fall below $80 before Day 22 Hour 0?
        price_below_80_by_day22 = 0
        min_p_before_22 = 999.0
        for s in range(11 * 24, 22 * 24):
            p_s = steps[s][0]["observation"]["market"]["prices"].get("STRAWBERRY", 120.0)
            if p_s < min_p_before_22: min_p_before_22 = p_s
            if p_s < 80.0:
                price_below_80_by_day22 = 1
                
        # Also determine if inventory crossed 10,000 before Day 22
        inv_crossed_10k_by_day22 = 0
        for s in range(11 * 24, 22 * 24):
            inv_s = steps[s][0]["observation"]["market"]["inventory"].get("STRAWBERRY", 10000)
            if inv_s >= 10000:
                inv_crossed_10k_by_day22 = 1
                break
                
        # Extract features for every hour between Day 11 Hour 0 and Day 18 Hour 0 (the critical hedge window!)
        for seat in (0, 1):
            opp_seat = 1 - seat
            
            opp_sales_history = []
            prev_inv = 10000
            
            for s in range(11 * 24, 18 * 24):
                obs = steps[s][seat]["observation"]
                day = s // 24
                hour = s % 24
                
                mkt = obs.market if hasattr(obs, "market") else obs["market"]
                prices = mkt["prices"]
                inv = mkt["inventory"]
                
                farms = obs.farms if hasattr(obs, "farms") else obs["farms"]
                f_our = farms[seat]
                f_opp = farms[opp_seat]
                
                our_straw = sum(1 for r in f_our["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                opp_straw = sum(1 for r in f_opp["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                
                # Check opponent sales in current step
                act_opp = steps[s+1][opp_seat].get("action", {}) if s + 1 < len(steps) else {}
                opp_sold_now = 0
                if isinstance(act_opp, dict):
                    for o in act_opp.get("market", []):
                        if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                            opp_sold_now += o[2]
                opp_sales_history.append(opp_sold_now)
                
                opp_sales_6h = sum(opp_sales_history[-6:])
                opp_sales_24h = sum(opp_sales_history[-24:])
                opp_sales_total = sum(opp_sales_history)
                
                inv_straw = int(inv.get("STRAWBERRY", 10000))
                p_straw = float(prices.get("STRAWBERRY", 120))
                delta_inv_1h = inv_straw - prev_inv
                prev_inv = inv_straw
                
                # Deterministic Physics Features:
                # Remaining hours to Day 22
                rem_days = (22 * 24 - s) / 24.0
                town_absorption_to_22 = rem_days * 13.0
                our_prod_to_22 = our_straw * (rem_days / 2.0)
                opp_prod_to_22 = opp_straw * (rem_days / 2.0)
                physics_net_pressure = (inv_straw + our_prod_to_22 + opp_prod_to_22) - (town_absorption_to_22 + 10000)
                
                dataset_rows.append({
                    "replay": os.path.basename(p),
                    "step": s,
                    "day": day,
                    "hour": hour,
                    "seat": seat,
                    "opp_straw_bushes": opp_straw,
                    "our_straw_bushes": our_straw,
                    "opp_sales_6h": opp_sales_6h,
                    "opp_sales_24h": opp_sales_24h,
                    "opp_sales_total": opp_sales_total,
                    "inv_straw": inv_straw,
                    "delta_inv_1h": delta_inv_1h,
                    "p_straw": p_straw,
                    "town_consumption_phase": hour % 4,
                    "physics_net_pressure": physics_net_pressure,
                    "target_flood_by_day22": price_below_80_by_day22,
                    "target_inv_10k_by_day22": inv_crossed_10k_by_day22
                })
    except Exception as e:
        continue

df = pd.DataFrame(dataset_rows)
print(f"Extracted {len(df):,} turn-level decision records across {df['replay'].nunique()} replays!")
print(f"Target Flood Rate: {df['target_flood_by_day22'].mean()*100:.1f}%")

df.to_csv("reports/opponent_realization_dataset.csv", index=False)
print("Saved dataset to reports/opponent_realization_dataset.csv")
