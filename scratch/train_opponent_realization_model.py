import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

df = pd.read_csv("reports/opponent_realization_dataset.csv")

features = [
    "opp_straw_bushes",
    "our_straw_bushes",
    "opp_sales_6h",
    "opp_sales_24h",
    "opp_sales_total",
    "inv_straw",
    "delta_inv_1h",
    "p_straw",
    "town_consumption_phase",
    "physics_net_pressure",
    "day",
    "hour"
]

target = "target_flood_by_day22"

X = df[features]
y = df[target]
groups = df["replay"]

gkf = GroupKFold(n_splits=5)

oof_preds = np.zeros(len(df))
feature_importances = np.zeros(len(features))

models = []

for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
    
    # Scale positive weight due to 5.3% imbalanced base rate
    pos_weight = (len(y_train) - sum(y_train)) / max(1, sum(y_train))
    
    clf = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        num_leaves=15,
        scale_pos_weight=pos_weight,
        random_state=42,
        verbosity=-1
    )
    
    clf.fit(X_train, y_train)
    oof_preds[val_idx] = clf.predict_proba(X_val)[:, 1]
    feature_importances += clf.feature_importances_ / 5.0
    models.append(clf)

auc = roc_auc_score(y, oof_preds)
pr_auc = average_precision_score(y, oof_preds)
brier = brier_score_loss(y, oof_preds)

print("=" * 80)
print("LIGHTGBM OPPONENT REALIZATION SPEED CLASSIFIER (OUT-OF-REPLAY 5-FOLD)")
print("=" * 80)
print(f"Out-of-Replay ROC-AUC:   {auc:.4f}")
print(f"Precision-Recall AUC:    {pr_auc:.4f} (Base rate: {y.mean():.4f})")
print(f"Brier Score Loss:        {brier:.4f}")
print("-" * 80)
print("FEATURE IMPORTANCE RANKING:")
fi_df = pd.DataFrame({"feature": features, "importance": feature_importances}).sort_values("importance", ascending=False)
for _, r in fi_df.iterrows():
    print(f"  {r['feature']:<25} : {r['importance']:>8.1f}")

# Inspect predicted flood probability across Day 11-18 for Soumi vs Arao
df["pred_flood_prob"] = oof_preds

print("\n" + "=" * 80)
print("PREDICTED FLOOD PROBABILITY TRAJECTORY (DAY 11 TO 16): SOUMI vs ARAO")
print("=" * 80)
for target_r, label in [("episode-104388418-replay.json", "Soumi (Active Flooder)"), ("episode-104379472-replay.json", "Arao (Passive Holder)")]:
    sub = df[df["replay"] == target_r]
    if len(sub) == 0: continue
    print(f"\n>>> {label}:")
    for d in [11, 12, 13, 14, 15, 16]:
        sub_d = sub[sub["day"] == d]
        if len(sub_d) == 0: continue
        avg_prob = sub_d["pred_flood_prob"].mean()
        avg_sales_24 = sub_d["opp_sales_24h"].mean()
        avg_inv = sub_d["inv_straw"].mean()
        print(f"  Day {d:02d} | Flood Prob: {avg_prob*100:>5.1f}% | Opp Sales 24h: {avg_sales_24:>5.1f} | Inv: {avg_inv:>5.0f}")

print("=" * 80)
