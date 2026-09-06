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

print(f"Phase 14: Scanning {len(replay_paths)} full replays to build ML Advisor Dataset...")

dataset_rows = []

for p in replay_paths:
    try:
        with open(p) as f: rep = json.load(f)
        steps = rep.get("steps", [])
        if len(steps) < 22 * 24: continue # need at least day 22
        
        # Ground Truth Target: Harmful saturation defined as:
        # Strawberry spot price drops below $80 before Day 22 Hour 0
        min_p_before_22 = min(
            steps[s][0]["observation"]["market"]["prices"].get("STRAWBERRY", 120.0)
            for s in range(11 * 24, 22 * 24)
        )
        harmful_flood = 1 if min_p_before_22 < 80.0 else 0
        
        # Also track the exact step of first deterministic trigger (I >= 9935 and delta_inv > 0)
        det_trigger_step = None
        prev_inv_track = 10000
        for s in range(15 * 24, 22 * 24):
            inv_s = int(steps[s][0]["observation"]["market"]["inventory"].get("STRAWBERRY", 10000))
            d_inv = inv_s - prev_inv_track
            prev_inv_track = inv_s
            if inv_s >= 9935 and d_inv > 0:
                det_trigger_step = s
                break
                
        # Extract features for every hour between Day 11 Hour 0 and Day 19 Hour 0
        for seat in (0, 1):
            opp_seat = 1 - seat
            opp_sales_history = []
            inv_history = []
            
            for s in range(11 * 24, 19 * 24):
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
                
                # Opponent sales in step
                act_opp = steps[s+1][opp_seat].get("action", {}) if s + 1 < len(steps) else {}
                opp_sold_now = 0
                if isinstance(act_opp, dict):
                    for o in act_opp.get("market", []):
                        if len(o) >= 3 and o[0] == "SELL" and o[1] == "STRAWBERRY":
                            opp_sold_now += min(o[2], 100) # cap empty macro orders
                opp_sales_history.append(opp_sold_now)
                
                inv_straw = int(inv.get("STRAWBERRY", 10000))
                inv_history.append(inv_straw)
                
                delta_inv_1h = inv_history[-1] - inv_history[-2] if len(inv_history) >= 2 else 0
                delta_inv_3h = inv_history[-1] - inv_history[-4] if len(inv_history) >= 4 else delta_inv_1h
                delta_inv_6h = inv_history[-1] - inv_history[-7] if len(inv_history) >= 7 else delta_inv_3h
                
                opp_sales_6h = sum(opp_sales_history[-6:])
                opp_sales_24h = sum(opp_sales_history[-24:])
                opp_sales_total = sum(opp_sales_history)
                
                p_straw = float(prices.get("STRAWBERRY", 120))
                
                # Deterministic physics baseline
                rem_days = (22 * 24 - s) / 24.0
                town_absorption = rem_days * 13.0
                our_pot_supply = our_straw * (rem_days / 2.0)
                opp_pot_supply = opp_straw * (rem_days / 2.0)
                physics_surplus = (inv_straw + our_pot_supply + opp_pot_supply) - (town_absorption + 10000)
                
                dataset_rows.append({
                    "replay": os.path.basename(p),
                    "step": s,
                    "day": day,
                    "hour": hour,
                    "seat": seat,
                    "opp_straw_bushes": opp_straw,
                    "our_straw_bushes": our_straw,
                    "market_straw_inventory": inv_straw,
                    "delta_inv_1h": delta_inv_1h,
                    "delta_inv_3h": delta_inv_3h,
                    "delta_inv_6h": delta_inv_6h,
                    "opp_sales_6h": opp_sales_6h,
                    "opp_sales_24h": opp_sales_24h,
                    "opp_sales_total": opp_sales_total,
                    "current_p_straw": p_straw,
                    "town_demand_phase": hour % 4,
                    "physics_surplus": physics_surplus,
                    "target_harmful_flood": harmful_flood,
                    "det_trigger_step": det_trigger_step if det_trigger_step is not None else 9999
                })
    except Exception as e:
        continue

df = pd.DataFrame(dataset_rows)
print(f"Phase 14 Dataset Built: {len(df):,} turn records across {df['replay'].nunique()} replays.")
print(f"Harmful Flood Rate: {df['target_harmful_flood'].mean()*100:.1f}%")

df.to_csv("reports/phase14_ml_advisor_dataset.csv", index=False)
print("Saved to reports/phase14_ml_advisor_dataset.csv")
