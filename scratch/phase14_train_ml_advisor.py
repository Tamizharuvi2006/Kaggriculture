import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score, average_precision_score

df = pd.read_csv("reports/phase14_ml_advisor_dataset.csv")

features = [
    "opp_straw_bushes",
    "our_straw_bushes",
    "market_straw_inventory",
    "delta_inv_1h",
    "delta_inv_3h",
    "delta_inv_6h",
    "opp_sales_6h",
    "opp_sales_24h",
    "opp_sales_total",
    "current_p_straw",
    "town_demand_phase",
    "physics_surplus",
    "day",
    "hour"
]

target = "target_harmful_flood"
groups = df["replay"]

# Let's filter to Days 14-17 (the crucial decision window)
sub_df = df[(df["day"] >= 14) & (df["day"] <= 17)].copy().reset_index(drop=True)
X = sub_df[features]
y = sub_df[target]
sub_groups = sub_df["replay"]

logo = LeaveOneGroupOut()

oof_preds = np.zeros(len(sub_df))

for train_idx, val_idx in logo.split(X, y, sub_groups):
    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
    
    if sum(y_train) == 0:
        oof_preds[val_idx] = 0.0
        continue
        
    pos_weight = (len(y_train) - sum(y_train)) / max(1, sum(y_train))
    clf = lgb.LGBMClassifier(
        n_estimators=50,
        learning_rate=0.05,
        num_leaves=7,
        scale_pos_weight=pos_weight,
        random_state=42,
        verbosity=-1
    )
    clf.fit(X_train, y_train)
    oof_preds[val_idx] = clf.predict_proba(X_val)[:, 1]

sub_df["pred_prob"] = oof_preds

# Evaluate per-replay prediction on Days 14-17
rep_eval = sub_df.groupby(["replay", "target_harmful_flood"])["pred_prob"].mean().reset_index()

print("=" * 80)
print("PHASE 14 ML FLOOD-PROBABILITY ADVISOR: LEAVE-ONE-REPLAY-OUT VALIDATION")
print("=" * 80)
try:
    auc = roc_auc_score(rep_eval["target_harmful_flood"], rep_eval["pred_prob"])
    pr_auc = average_precision_score(rep_eval["target_harmful_flood"], rep_eval["pred_prob"])
    print(f"Replay-Level ROC-AUC on Days 14-17: {auc:.4f}")
    print(f"Replay-Level PR-AUC on Days 14-17:  {pr_auc:.4f} (Base rate: {rep_eval['target_harmful_flood'].mean():.4f})")
except Exception as e:
    print("Metrics error:", e)

print("-" * 80)
print("HIGHEST PREDICTED FLOOD PROBABILITY REPLAYS (DAYS 14-17):")
for _, r in rep_eval.sort_values("pred_prob", ascending=False).head(10).iterrows():
    actual_str = "COLLAPSED" if r["target_harmful_flood"] == 1 else "STABLE"
    print(f"  {r['replay']:<35} | Pred P(Flood): {r['pred_prob']*100:>5.1f}% | Actual: {actual_str}")

print("-" * 80)
print("BENCHMARK REPLAYS (SOUMI, ARAO, HIGH CEILING):")
for r_name, label in [("episode-104388418-replay.json", "Soumi (Active Flooder)"), ("episode-104379472-replay.json", "Arao (Passive Holder)")]:
    sub_r = rep_eval[rep_eval["replay"] == r_name]
    if len(sub_r) > 0:
        p_val = sub_r["pred_prob"].values[0]
        act_val = sub_r["target_harmful_flood"].values[0]
        act_str = "COLLAPSED" if act_val == 1 else "STABLE"
        print(f"  {label:<25} ({r_name}) | Pred P: {p_val*100:>5.1f}% | Actual: {act_str}")

print("=" * 80)
