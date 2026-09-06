import sys
sys.path.insert(0, r"D:\kaggriculture")

import pandas as pd
import numpy as np

data_path = r"D:\kaggriculture\data\market_decision_dataset_15seeds.csv"
print(f"Loading dataset from {data_path}...")
df = pd.read_csv(data_path)

# Evaluate strictly on unseen validation seeds (2012-2015)
val_seeds = list(range(2012, 2016))
val_df = df[df["seed"].isin(val_seeds)].copy()
n_matches = len(val_seeds)

print("=" * 105)
print("OFFLINE ECONOMIC VALUE AUDIT: ACTUAL DOLLAR VALUE OF ACTING ON CRASH TRIGGER")
print(f"Evaluated across {n_matches} unseen validation matches (Seeds {val_seeds})")
print("=" * 105)

for commodity in ["MILK", "STRAWBERRY"]:
    c_df = val_df[val_df["commodity"] == commodity].copy()
    p_scarcity = 180.0 if commodity == "MILK" else 130.0
    
    # Condition: Trigger fires AND shed actually has inventory to sell
    trigger_mask = (c_df["spot_price"] >= p_scarcity) & (c_df["di_1"] > 0)
    actionable_mask = trigger_mask & (c_df["qty_in_shed"] > 0)
    
    all_triggers = c_df[trigger_mask]
    actionable = c_df[actionable_mask]
    
    n_all_trig = len(all_triggers)
    n_act_trig = len(actionable)
    
    # 1. Price drift across ALL trigger events (regardless of shed qty)
    dp1_all = all_triggers["target_price_t1"] - all_triggers["spot_price"]
    dp3_all = all_triggers["target_price_t3"] - all_triggers["spot_price"]
    
    # 2. Dollar economic impact on ACTIONABLE trigger events (where shed had inventory)
    if n_act_trig > 0:
        total_units = actionable["qty_in_shed"].sum()
        avg_units = actionable["qty_in_shed"].mean()
        
        # Immediate revenue
        rev_now = actionable["spot_price"] * actionable["qty_in_shed"]
        # Revenue if delayed by 1 turn
        rev_t1 = actionable["target_price_t1"] * actionable["qty_in_shed"]
        # Revenue if delayed by 3 turns
        rev_t3 = actionable["target_price_t3"] * actionable["qty_in_shed"]
        
        # Economic benefit of selling now vs waiting
        benefit_vs_t1 = rev_now - rev_t1
        benefit_vs_t3 = rev_now - rev_t3
        
        tot_benefit_t1 = benefit_vs_t1.sum()
        tot_benefit_t3 = benefit_vs_t3.sum()
        
        benefit_per_unit_t1 = tot_benefit_t1 / total_units if total_units > 0 else 0
        benefit_per_unit_t3 = tot_benefit_t3 / total_units if total_units > 0 else 0
        
        benefit_per_trig_t1 = tot_benefit_t1 / n_act_trig
        benefit_per_trig_t3 = tot_benefit_t3 / n_act_trig
        
        benefit_per_match_t1 = tot_benefit_t1 / n_matches
        benefit_per_match_t3 = tot_benefit_t3 / n_matches
    else:
        tot_benefit_t1 = tot_benefit_t3 = 0
        benefit_per_unit_t1 = benefit_per_unit_t3 = 0
        benefit_per_trig_t1 = benefit_per_trig_t3 = 0
        benefit_per_match_t1 = benefit_per_match_t3 = 0
        total_units = avg_units = 0

    print(f"\n>>> COMMODITY: {commodity} (Threshold: Spot >= ${p_scarcity:.0f} AND di_1 > 0)")
    print(f"  Total Market Trigger Events:        {n_all_trig} ({n_all_trig/n_matches:.1f} per match)")
    print(f"  Actionable Events (Shed > 0):       {n_act_trig} ({n_act_trig/n_matches:.1f} per match)")
    print(f"  Total Inventory Exposed:            {total_units:,.0f} units (Avg: {avg_units:.1f} units/event)")
    print(f"  Average Price Drift (All Events):   1-turn: ${dp1_all.mean():+.2f} | 3-turn: ${dp3_all.mean():+.2f}")
    print("-" * 80)
    print(f"  ECONOMIC BENEFIT OF SELLING IMMEDIATELY (AVOIDING DELAY):")
    print(f"  Horizon t+1 (1-Turn Avoidance):")
    print(f"    - Benefit per Unit Sold:          +${benefit_per_unit_t1:.2f} / unit")
    print(f"    - Benefit per Actionable Trigger: +${benefit_per_trig_t1:,.2f}")
    print(f"    - Total Realized Lift per Match:  +${benefit_per_match_t1:,.2f} / match")
    print(f"  Horizon t+3 (3-Turn Avoidance):")
    print(f"    - Benefit per Unit Sold:          +${benefit_per_unit_t3:.2f} / unit")
    print(f"    - Benefit per Actionable Trigger: +${benefit_per_trig_t3:,.2f}")
    print(f"    - Total Realized Lift per Match:  +${benefit_per_match_t3:,.2f} / match")

print("\n" + "=" * 105)
print("AUDIT COMPLETE — RIGOROUS OFFLINE REVENUE SIZING FINISHED.")
print("=" * 105)
