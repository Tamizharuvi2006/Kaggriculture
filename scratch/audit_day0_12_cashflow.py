import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json, time
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

# Target seeds to compare:
# 1. Worst Floor: Soumi Ghosh Seat 1 (replay: episode-104388418-replay.json) -> Final score: $21,856
# 2. Low Floor Live Seed: Ep 105105439 ($38k vs zZx Hee) -> seed 334330253
# 3. High Ceiling: Ep 105112452 Seat 1 -> seed 628719714 (Final score: $95,831)
# 4. High Elo Benchmark: RicardoLópez Seat 1 -> episode-104475527-replay.json

benchmarks = [
    {"label": "WORST_FLOOR_Soumi_S1 ($21.8k)", "type": "replay", "file": "episode-104388418-replay.json", "seat": 1},
    {"label": "LOW_FLOOR_zZxHee_S0 ($38.0k)", "type": "seed", "seed": 334330253, "seat": 0},
    {"label": "HIGH_CEILING_628M_S1 ($95.8k)", "type": "seed", "seed": 628719714, "seat": 1},
]

def run_forensic_cashflow(target):
    if target["type"] == "replay":
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", target["file"])
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        seat = target["seat"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
    else:
        seed = target["seed"]
        seat = target["seat"]
        steps = range(721)
        opp_actions = None
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    # Forensic tracking
    days_data = {}
    current_day_data = None
    
    prev_money = 3000
    prev_day = -1
    
    for step in range(len(steps) - 1):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        
        if day > 13: break # Focus on Days 0 to 12
        
        if day != prev_day:
            if current_day_data is not None:
                days_data[prev_day] = current_day_data
            prev_day = day
            current_day_data = {
                "day": day,
                "start_cash": obs.farms[seat].money,
                "min_cash": obs.farms[seat].money,
                "end_cash": obs.farms[seat].money,
                "seed_spent": 0,
                "animal_spent": 0,
                "wages_spent": 0,
                "land_spent": 0,
                "crop_rev": 0,
                "animal_rev": 0,
                "fert_rev": 0,
                "hires": 0,
                "cows": 0,
                "sheep": 0,
                "planted_tiles": 0,
                "unwatered_tiles": 0,
                "mature_tiles": 0
            }
            
        cur_money = obs.farms[seat].money
        if cur_money < current_day_data["min_cash"]:
            current_day_data["min_cash"] = cur_money
            
        # Get actions
        if target["type"] == "replay":
            if seat == 0:
                act0 = rc2_mod.agent(env.state[0].observation)
                act1 = opp_actions[step]
            else:
                act0 = opp_actions[step]
                act1 = rc2_mod.agent(env.state[1].observation)
        else:
            # Self-play against RC2
            act0 = rc2_mod.agent(env.state[0].observation)
            act1 = rc2_mod.agent(env.state[1].observation)
            
        agent_act = act0 if seat == 0 else act1
        
        # Track market order actions from agent
        mkt_orders = agent_act.get("market", []) if isinstance(agent_act, dict) else []
        for ord_item in mkt_orders:
            if not ord_item or len(ord_item) < 2: continue
            otype = ord_item[0]
            target_item = ord_item[1]
            qty = ord_item[2] if len(ord_item) > 2 else 1
            
            p_val = obs.market.prices.get(target_item, 0)
            if otype == "BUY_SEED":
                current_day_data["seed_spent"] += qty * p_val
            elif otype in ("BUY_ANIMAL", "BUY_COW", "BUY_SHEEP"):
                current_day_data["animal_spent"] += qty * p_val
            elif otype == "BUY_LAND":
                current_day_data["land_spent"] += 1000
            elif otype == "HIRE":
                current_day_data["hires"] += 1
            elif otype == "SELL":
                if target_item == "FERTILIZER":
                    current_day_data["fert_rev"] += qty * p_val
                elif target_item in ("MILK", "WOOL"):
                    current_day_data["animal_rev"] += qty * p_val
                else:
                    current_day_data["crop_rev"] += qty * p_val
                    
        # Step environment
        env.step([act0, act1])
        
        # Count tile statuses
        farm = env.state[seat].observation.farms[seat]
        cows = 0
        sheep = 0
        planted = 0
        unwatered = 0
        mature = 0
        for r in range(len(farm.tiles)):
            for c in range(len(farm.tiles[r])):
                t = farm.tiles[r][c]
                if isinstance(t, dict):
                    if t.get("animal") == "COW": cows += 1
                    elif t.get("animal") == "SHEEP": sheep += 1
                    if t.get("crop"):
                        planted += 1
                        if not t.get("watered", True): unwatered += 1
                        if t.get("stage") == "MATURE" or t.get("age", 0) >= 10: mature += 1
        current_day_data["cows"] = cows
        current_day_data["sheep"] = sheep
        current_day_data["planted_tiles"] = planted
        current_day_data["unwatered_tiles"] = unwatered
        current_day_data["mature_tiles"] = mature
        current_day_data["end_cash"] = farm.money
        
    if current_day_data:
        days_data[prev_day] = current_day_data
        
    return days_data

print("=" * 115)
print("DAY 0 TO 12 FORENSIC CASH-FLOW COMPARISON: WORST FLOOR vs HIGH CEILING")
print("=" * 115)

all_forensics = {}
for target in benchmarks:
    print(f"\nRunning forensic simulation for: {target['label']}...")
    data = run_forensic_cashflow(target)
    all_forensics[target["label"]] = data

# Print side-by-side day-by-day cash table
print("\n" + "=" * 115)
print(f"{'DAY':<4} | {'METRIC':<18} | {'WORST FLOOR ($21.8k)':>25} | {'LOW FLOOR ($38k)':>25} | {'HIGH CEILING ($95.8k)':>25}")
print("-" * 115)

metrics_to_print = ["start_cash", "min_cash", "end_cash", "seed_spent", "animal_spent", "crop_rev", "unwatered_tiles"]

for d in range(0, 13):
    print(f"DAY {d:02d} " + "-" * 108)
    for m in metrics_to_print:
        v_worst = all_forensics["WORST_FLOOR_Soumi_S1 ($21.8k)"].get(d, {}).get(m, 0)
        v_low   = all_forensics["LOW_FLOOR_zZxHee_S0 ($38.0k)"].get(d, {}).get(m, 0)
        v_high  = all_forensics["HIGH_CEILING_628M_S1 ($95.8k)"].get(d, {}).get(m, 0)
        
        fmt_worst = f"${v_worst:>9,.0f}" if "cash" in m or "spent" in m or "rev" in m else f"{v_worst:>10}"
        fmt_low   = f"${v_low:>9,.0f}"   if "cash" in m or "spent" in m or "rev" in m else f"{v_low:>10}"
        fmt_high  = f"${v_high:>9,.0f}"  if "cash" in m or "spent" in m or "rev" in m else f"{v_high:>10}"
        
        print(f"     | {m:<18} | {fmt_worst:>25} | {fmt_low:>25} | {fmt_high:>25}")

# Save JSON
with open(r"D:\kaggriculture\reports\DAY0_12_CASHFLOW_FORENSICS.json", "w") as f:
    json.dump(all_forensics, f, indent=2)
print("\nForensic JSON saved to reports/DAY0_12_CASHFLOW_FORENSICS.json")
