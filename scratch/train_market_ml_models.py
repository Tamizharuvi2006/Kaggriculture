import sys
sys.path.insert(0, r"D:\kaggriculture")

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score, accuracy_score, classification_report

data_path = r"D:\kaggriculture\data\market_decision_dataset_15seeds.csv"
print(f"Loading dataset from {data_path}...")
df = pd.read_csv(data_path)

# Seed-based out-of-sample split (Strict Seed Separation!)
train_seeds = list(range(2001, 2012)) # 11 seeds
val_seeds = list(range(2012, 2016))   # 4 seeds

train_df = df[df["seed"].isin(train_seeds)].copy()
val_df = df[df["seed"].isin(val_seeds)].copy()

print(f"Train Rows: {len(train_df):,} across seeds {train_seeds}")
print(f"Val Rows:   {len(val_df):,} across unseen seeds {val_seeds}")

# Feature columns (strictly observable at turn t)
feature_cols = [
    "day", "hour", "spot_price", "market_inventory",
    "dp_1", "dp_3", "dp_6", "di_1", "di_3", "di_6",
    "cash", "shed_total", "shed_free_space", "workers", "liquidity_urgency",
    "p0_cows", "p0_straws", "opp_cows", "opp_straws", "opp_cash"
]

results_report = {}

for commodity in ["STRAWBERRY", "MILK"]:
    print("\n" + "=" * 90)
    print(f"COMMODITY: {commodity} — MODEL EVALUATION ON UNSEEN SEEDS")
    print("=" * 90)
    
    c_train = train_df[train_df["commodity"] == commodity]
    c_val = val_df[val_df["commodity"] == commodity]
    
    X_train = c_train[feature_cols]
    X_val = c_val[feature_cols]
    
    # -------------------------------------------------------------
    # TASK 1: Price Forecasting at Horizon t+3 (Regression)
    # -------------------------------------------------------------
    y_train_p3 = c_train["target_price_t3"]
    y_val_p3 = c_val["target_price_t3"]
    
    # Baseline 1: Persistence (future price = spot price)
    pred_persist = c_val["spot_price"]
    mae_persist = mean_absolute_error(y_val_p3, pred_persist)
    rmse_persist = np.sqrt(mean_squared_error(y_val_p3, pred_persist))
    r2_persist = r2_score(y_val_p3, pred_persist)
    
    # Baseline 2: Random Forest Regressor
    rf_reg = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
    rf_reg.fit(X_train, y_train_p3)
    pred_rf = rf_reg.predict(X_val)
    mae_rf = mean_absolute_error(y_val_p3, pred_rf)
    rmse_rf = np.sqrt(mean_squared_error(y_val_p3, pred_rf))
    r2_rf = r2_score(y_val_p3, pred_rf)
    
    # Baseline 3: LightGBM Regressor
    lgb_reg = lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1)
    lgb_reg.fit(X_train, y_train_p3)
    pred_lgb = lgb_reg.predict(X_val)
    mae_lgb = mean_absolute_error(y_val_p3, pred_lgb)
    rmse_lgb = np.sqrt(mean_squared_error(y_val_p3, pred_lgb))
    r2_lgb = r2_score(y_val_p3, pred_lgb)
    
    print(f"--- Task 1: Price Forecast t+3 (Spot Range: ${c_val['spot_price'].min():.0f} - ${c_val['spot_price'].max():.0f}) ---")
    print(f"{'Model':<25} | {'MAE':>10} | {'RMSE':>10} | {'R^2 Score':>12}")
    print("-" * 65)
    print(f"{'1. Persistence (Spot)':<25} | ${mae_persist:>9.2f} | ${rmse_persist:>9.2f} | {r2_persist:>12.4f}")
    print(f"{'2. Random Forest':<25} | ${mae_rf:>9.2f} | ${rmse_rf:>9.2f} | {r2_rf:>12.4f}")
    print(f"{'3. LightGBM':<25} | ${mae_lgb:>9.2f} | ${rmse_lgb:>9.2f} | {r2_lgb:>12.4f}")
    
    # -------------------------------------------------------------
    # TASK 2: Crash Risk Prediction (Binary Classification)
    # -------------------------------------------------------------
    y_train_crash = c_train["target_crash_3"]
    y_val_crash = c_val["target_crash_3"]
    crash_rate = y_val_crash.mean() * 100
    
    rf_clf = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42, n_jobs=-1)
    rf_clf.fit(X_train, y_train_crash)
    prob_rf = rf_clf.predict_proba(X_val)[:, 1]
    auc_rf = roc_auc_score(y_val_crash, prob_rf) if len(np.unique(y_val_crash)) > 1 else 0.5
    
    lgb_clf = lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, verbose=-1)
    lgb_clf.fit(X_train, y_train_crash)
    prob_lgb = lgb_clf.predict_proba(X_val)[:, 1]
    auc_lgb = roc_auc_score(y_val_crash, prob_lgb) if len(np.unique(y_val_crash)) > 1 else 0.5
    
    print(f"\n--- Task 2: Crash Detection (Price Drop >= 25% within 3 turns, Rate: {crash_rate:.1f}%) ---")
    print(f"{'Model':<25} | {'AUC-ROC':>10} | {'Crash Accuracy':>15}")
    print("-" * 65)
    print(f"{'Random Forest':<25} | {auc_rf:>10.4f} | {accuracy_score(y_val_crash, prob_rf >= 0.5):>14.2%}")
    print(f"{'LightGBM':<25} | {auc_lgb:>10.4f} | {accuracy_score(y_val_crash, prob_lgb >= 0.5):>14.2%}")
    
    # -------------------------------------------------------------
    # TASK 3: Wait vs Sell Decision (Binary Classification)
    # -------------------------------------------------------------
    y_train_wait = c_train["target_wait_advantage"]
    y_val_wait = c_val["target_wait_advantage"]
    wait_rate = y_val_wait.mean() * 100
    
    lgb_wait = lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, verbose=-1)
    lgb_wait.fit(X_train, y_train_wait)
    prob_wait = lgb_wait.predict_proba(X_val)[:, 1]
    auc_wait = roc_auc_score(y_val_wait, prob_wait) if len(np.unique(y_val_wait)) > 1 else 0.5
    
    print(f"\n--- Task 3: Wait vs Sell Advantage (Rate where Wait t+3 > Sell Now: {wait_rate:.1f}%) ---")
    print(f"{'LightGBM Wait Classifier':<25} | AUC-ROC: {auc_wait:.4f} | Accuracy: {accuracy_score(y_val_wait, prob_wait >= 0.5):.2%}")

    # Top Feature Importances for LightGBM
    importances = lgb_reg.feature_importances_
    sorted_idx = np.argsort(importances)[::-1][:6]
    top_features = [f"{feature_cols[i]}: {importances[i]}" for i in sorted_idx]
    print(f"\nTop 6 Predictive Features for {commodity} Price:")
    for rank, idx in enumerate(sorted_idx, 1):
        print(f"  {rank}. {feature_cols[idx]:<18} (Importance: {importances[idx]})")

print("\n" + "=" * 90)
print("TRAINING AND OUT-OF-SAMPLE VALIDATION COMPLETE!")
print("=" * 90)
