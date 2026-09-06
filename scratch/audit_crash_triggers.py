import sys
sys.path.insert(0, r"D:\kaggriculture")

import pandas as pd
import numpy as np

data_path = r"D:\kaggriculture\data\market_decision_dataset_15seeds.csv"
print(f"Loading dataset from {data_path}...")
df = pd.read_csv(data_path)

# Evaluate STRICTLY on the unseen validation seeds (2012-2015)
val_seeds = list(range(2012, 2016))
val_df = df[df["seed"].isin(val_seeds)].copy()
print(f"Validation dataset: {len(val_df):,} rows across unseen seeds {val_seeds}\n")

# Compute forward price changes: Delta P_k = P_{t+k} - P_t
val_df["dp_fut_1"] = val_df["target_price_t1"] - val_df["spot_price"]
val_df["dp_fut_3"] = val_df["target_price_t3"] - val_df["spot_price"]
val_df["dp_fut_6"] = val_df["target_price_t6"] - val_df["spot_price"]

def audit_trigger(sub_df, condition_mask, label, commodity, horizon=3):
    total_turns = len(sub_df)
    active_shed_turns = len(sub_df[sub_df["qty_in_shed"] > 0])
    
    triggered = sub_df[condition_mask]
    n_trig = len(triggered)
    
    if n_trig == 0:
        return {
            "label": label, "triggers": 0, "trig_rate": "0.0%",
            "mean_dp1": 0, "mean_dp3": 0, "mean_dp6": 0,
            "median_dp3": 0, "precision_drop": "N/A", "fpr": "N/A", "recall_drop": "N/A"
        }
        
    # Forward price movements when triggered
    mean_dp1 = triggered["dp_fut_1"].mean()
    mean_dp3 = triggered["dp_fut_3"].mean()
    mean_dp6 = triggered["dp_fut_6"].mean()
    med_dp3 = triggered["dp_fut_3"].median()
    
    # Ground truth definition of a negative price movement over horizon turns
    actual_drops = sub_df["dp_fut_3"] < 0
    actual_material_drops = sub_df["dp_fut_3"] <= -2.0 # Dropped at least $2
    
    # Precision: when triggered, what % of the time did price drop?
    true_positives = (triggered["dp_fut_3"] < 0).sum()
    precision = true_positives / n_trig
    
    # False Positive: trigger fired, but price did NOT drop (stayed same or rose)
    false_positives = (triggered["dp_fut_3"] >= 0).sum()
    fpr = false_positives / n_trig
    
    # Recall: of all material drops in the game, how many did this trigger catch?
    total_material_drops = actual_material_drops.sum()
    caught_drops = (triggered["dp_fut_3"] <= -2.0).sum()
    recall = (caught_drops / total_material_drops) if total_material_drops > 0 else 0
    
    return {
        "label": label,
        "triggers": n_trig,
        "trig_rate": f"{n_trig / total_turns:.1%}",
        "mean_dp1": f"${mean_dp1:+.2f}",
        "mean_dp3": f"${mean_dp3:+.2f}",
        "mean_dp6": f"${mean_dp6:+.2f}",
        "median_dp3": f"${med_dp3:+.2f}",
        "precision_drop": f"{precision:.1%}",
        "fpr": f"{fpr:.1%}",
        "recall_drop": f"{recall:.1%}"
    }

for commodity in ["MILK", "STRAWBERRY"]:
    c_df = val_df[val_df["commodity"] == commodity].copy()
    p_base = 160.0 if commodity == "MILK" else 120.0
    p_scarcity = 180.0 if commodity == "MILK" else 130.0
    
    print("=" * 115)
    print(f"OFFLINE TRIGGER AUDIT: {commodity} (Base Price: ${p_base:.0f}, Scarcity Threshold: ${p_scarcity:.0f})")
    print("=" * 115)
    
    triggers = [
        # Candidate 1: 1-step velocity
        (c_df["spot_price"] >= p_scarcity) & (c_df["di_1"] > 0),
        "P >= High AND di_1 > 0",
        
        # Candidate 2: 3-step velocity
        (c_df["spot_price"] >= p_scarcity) & (c_df["di_3"] > 0),
        "P >= High AND di_3 > 0",
        
        # Candidate 3: 3-step material velocity (di_3 >= 2)
        (c_df["spot_price"] >= p_scarcity) & (c_df["di_3"] >= 2),
        "P >= High AND di_3 >= 2",
        
        # Candidate 4: 3-step heavy velocity (di_3 >= 5)
        (c_df["spot_price"] >= p_scarcity) & (c_df["di_3"] >= 5),
        "P >= High AND di_3 >= 5",
        
        # Candidate 5: Dual confirmation (di_1 > 0 OR dp_1 < 0)
        (c_df["spot_price"] >= p_scarcity) & ((c_df["di_1"] > 0) | (c_df["dp_1"] < 0)),
        "P >= High AND (di_1 > 0 or dp_1 < 0)",
        
        # Candidate 6: Simple High Spot Price alone (Control Benchmark)
        (c_df["spot_price"] >= p_scarcity),
        "P >= High (Spot Only Control)"
    ]
    
    records = []
    for i in range(0, len(triggers), 2):
        mask = triggers[i]
        lbl = triggers[i+1]
        rec = audit_trigger(c_df, mask, lbl, commodity)
        records.append(rec)
        
    res_df = pd.DataFrame(records)
    print(f"{'Trigger Definition':<35} | {'Triggers':>8} | {'Rate':>6} | {'Mean dP_3':>10} | {'Med dP_3':>10} | {'Mean dP_6':>10} | {'Precision':>10} | {'FPR':>8} | {'Recall':>8}")
    print("-" * 115)
    for _, r in res_df.iterrows():
        print(f"{r['label']:<35} | {r['triggers']:>8} | {r['trig_rate']:>6} | {r['mean_dp3']:>10} | {r['median_dp3']:>10} | {r['mean_dp6']:>10} | {r['precision_drop']:>10} | {r['fpr']:>8} | {r['recall_drop']:>8}")
    print()

print("=" * 115)
print("AUDIT COMPLETE — ALL METRICS COMPUTED ON UNSEEN SEEDS 2012-2015.")
print("=" * 115)
