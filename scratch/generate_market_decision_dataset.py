import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json, time, importlib
import numpy as np
import pandas as pd
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

# Commodities to monitor
COMMODITIES = ["MILK", "STRAWBERRY", "WOOL", "MELON", "FERTILIZER", "CARROT", "WHEAT"]

# Training seeds (strictly disjoint from the 10 Phase-11 holdout seeds!)
TRAIN_SEEDS = [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015]

def extract_game_data(seed):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    # Store trajectory of observations and market states
    traj = []
    
    for step in range(720):
        if env.done: break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        
        # Save snapshot for Player 0
        f0 = obs0.farms[0]
        f1 = obs0.farms[1]
        priv0 = env.state[0].observation.private
        shed0 = priv0.get("shed", {})
        mkt = obs0.market
        prices = dict(mkt.prices)
        inv = dict(mkt.inventory)
        
        # Count visible assets
        p0_cows = 0
        p0_sheep = 0
        p0_straws = 0
        p1_cows = 0
        p1_sheep = 0
        p1_straws = 0
        for r in range(len(f0.tiles)):
            for c in range(len(f0.tiles[r])):
                t0 = f0.tiles[r][c]
                t1 = f1.tiles[r][c]
                if isinstance(t0, dict):
                    if t0.get("animal") == "COW": p0_cows += 1
                    elif t0.get("animal") == "SHEEP": p0_sheep += 1
                    elif t0.get("crop") == "STRAWBERRY": p0_straws += 1
                if isinstance(t1, dict):
                    if t1.get("animal") == "COW": p1_cows += 1
                    elif t1.get("animal") == "SHEEP": p1_sheep += 1
                    elif t1.get("crop") == "STRAWBERRY": p1_straws += 1
                    
        # Compute impending wage liability today
        hires_today = f0.hires_today
        # Next hire cost
        a, b = 1, 1
        for _ in range(hires_today): a, b = b, a + b
        next_hire_wage = a
        
        traj.append({
            "step": step,
            "day": obs0.day,
            "hour": obs0.hour,
            "cash": f0.money,
            "shed_total": sum(shed0.values()),
            "workers": len(f0.hands) + 1,
            "next_hire_wage": next_hire_wage,
            "p0_cows": p0_cows,
            "p0_sheep": p0_sheep,
            "p0_straws": p0_straws,
            "p1_cows": p1_cows,
            "p1_sheep": p1_sheep,
            "p1_straws": p1_straws,
            "p1_cash": f1.money,
            "shed_counts": {c: shed0.get(c, 0) for c in COMMODITIES},
            "prices": prices,
            "inventories": inv
        })
        
        act0 = rc2_mod.agent(obs0)
        act1 = rc2_mod.agent(obs1)
        env.step([act0, act1])
        
    # Now compute lag velocity features and forward horizon targets
    rows = []
    T = len(traj)
    for t in range(T):
        s = traj[t]
        
        # Lag features (past 1, 3, 6 turns)
        p_curr = s["prices"]
        i_curr = s["inventories"]
        
        p_lag1 = traj[t - 1]["prices"] if t >= 1 else p_curr
        p_lag3 = traj[t - 3]["prices"] if t >= 3 else p_curr
        p_lag6 = traj[t - 6]["prices"] if t >= 6 else p_curr
        
        i_lag1 = traj[t - 1]["inventories"] if t >= 1 else i_curr
        i_lag3 = traj[t - 3]["inventories"] if t >= 3 else i_curr
        i_lag6 = traj[t - 6]["inventories"] if t >= 6 else i_curr
        
        # Future price targets (t+1, t+3, t+6)
        p_fut1 = traj[t + 1]["prices"] if t + 1 < T else p_curr
        p_fut3 = traj[t + 3]["prices"] if t + 3 < T else p_curr
        p_fut6 = traj[t + 6]["prices"] if t + 6 < T else p_curr
        
        # For each commodity, create a decision row
        for c in COMMODITIES:
            spot = p_curr[c]
            qty = s["shed_counts"][c]
            
            # Velocities
            dp1 = spot - p_lag1[c]
            dp3 = spot - p_lag3[c]
            dp6 = spot - p_lag6[c]
            
            di1 = i_curr[c] - i_lag1[c]
            di3 = i_curr[c] - i_lag3[c]
            di6 = i_curr[c] - i_lag6[c]
            
            # Future targets
            fut1 = p_fut1[c]
            fut3 = p_fut3[c]
            fut6 = p_fut6[c]
            
            # Economic targets
            crash_3 = 1 if (spot > 1 and (spot - fut3) / spot >= 0.25) else 0
            rev_now = spot * qty
            rev_fut3 = fut3 * qty
            rev_delta3 = rev_fut3 - rev_now
            
            # Liquidity pressure: is cash low relative to wages and seeds?
            liquidity_urgency = 1 if s["cash"] < 600 else (2 if s["cash"] < 300 else 0)
            
            rows.append({
                "seed": seed,
                "step": s["step"],
                "day": s["day"],
                "hour": s["hour"],
                "commodity": c,
                "qty_in_shed": qty,
                "spot_price": spot,
                "market_inventory": i_curr[c],
                "dp_1": dp1,
                "dp_3": dp3,
                "dp_6": dp6,
                "di_1": di1,
                "di_3": di3,
                "di_6": di6,
                "cash": s["cash"],
                "shed_total": s["shed_total"],
                "shed_free_space": max(0, 100 - s["shed_total"]),
                "workers": s["workers"],
                "liquidity_urgency": liquidity_urgency,
                "p0_cows": s["p0_cows"],
                "p0_straws": s["p0_straws"],
                "opp_cows": s["p1_cows"],
                "opp_straws": s["p1_straws"],
                "opp_cash": s["p1_cash"],
                # Targets
                "target_price_t1": fut1,
                "target_price_t3": fut3,
                "target_price_t6": fut6,
                "target_crash_3": crash_3,
                "target_rev_delta_3": rev_delta3,
                "target_wait_advantage": 1 if rev_delta3 > 0 else 0
            })
    return rows

print("Generating clean, leakage-free training dataset across 15 independent seeds...")
all_rows = []
for seed in TRAIN_SEEDS:
    t0 = time.time()
    rows = extract_game_data(seed)
    all_rows.extend(rows)
    print(f"  Seed {seed} complete ({len(rows):,} rows) in {time.time()-t0:.1f}s")

df = pd.DataFrame(all_rows)
out_path = r"D:\kaggriculture\data\market_decision_dataset_15seeds.csv"
df.to_csv(out_path, index=False)
print(f"\nSuccessfully generated {len(df):,} decision rows across {len(TRAIN_SEEDS)} seeds!")
print(f"Saved to: {out_path}")
print(df.head(3))
