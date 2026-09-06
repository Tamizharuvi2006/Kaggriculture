import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score

data_path = r"D:\kaggriculture\data\market_decision_dataset_15seeds.csv"
df = pd.read_csv(data_path)

train_seeds = list(range(2001, 2012))
val_seeds = list(range(2012, 2016))

train_df = df[df["seed"].isin(train_seeds)].copy()
val_df = df[df["seed"].isin(val_seeds)].copy()

features = [
    "spot_price", "market_inventory", "dp_1", "dp_3", "di_1", "di_3",
    "hour", "day", "cash", "shed_total", "opp_cows", "opp_straws"
]

print("=" * 80)
print("TRAINING COMPACT, DEPENDENCY-FREE CRASH DETECTION TREES (DEPTH <= 3)")
print("=" * 80)

tree_code = {}

for commodity in ["STRAWBERRY", "MILK"]:
    c_train = train_df[train_df["commodity"] == commodity]
    c_val = val_df[val_df["commodity"] == commodity]
    
    X_train = c_train[features]
    y_train = c_train["target_crash_3"]
    X_val = c_val[features]
    y_val = c_val["target_crash_3"]
    
    # Train depth-3 tree
    tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=20, random_state=42)
    tree.fit(X_train, y_train)
    
    prob_val = tree.predict_proba(X_val)[:, 1] if len(tree.classes_) > 1 else np.zeros(len(X_val))
    auc = roc_auc_score(y_val, prob_val) if len(np.unique(y_val)) > 1 else 0.5
    
    print(f"\n>>> Commodity: {commodity}")
    print(f"Validation AUC-ROC: {auc:.4f}")
    print(f"Tree Structure:\n{export_text(tree, feature_names=features)}")

print("\nFinished compact tree inspection.")
