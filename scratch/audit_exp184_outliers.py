import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np

CSV_PATH = r"D:\kaggriculture\data\exp184_residual_q_dataset.csv"

def audit():
    df = pd.read_csv(CSV_PATH)
    print("=" * 90)
    print("EXP184 FORENSIC AUDIT: 276,316 COUNTERFACTUAL DATASET")
    print("=" * 90)
    print(f"Total entries: {len(df):,}")
    pos_0 = (df['delta_reward'] > 0).sum()
    pos_500 = (df['delta_reward'] > 500).sum()
    pos_1000 = (df['delta_reward'] > 1000).sum()
    pos_5000 = (df['delta_reward'] > 5000).sum()
    pos_10000 = (df['delta_reward'] > 10000).sum()

    print(f"Positive gains (Δ > $0)       : {pos_0:,} ({pos_0/len(df)*100:.2f}%)")
    print(f"Gains > +$500                 : {pos_500:,} ({pos_500/len(df)*100:.2f}%)")
    print(f"High-value gains (> +$1,000)  : {pos_1000:,} ({pos_1000/len(df)*100:.2f}%)")
    print(f"Substantial gains (> +$5,000) : {pos_5000:,} ({pos_5000/len(df)*100:.2f}%)")
    print(f"Massive gains (> +$10,000)    : {pos_10000:,} ({pos_10000/len(df)*100:.2f}%)")

    print("\n" + "=" * 90)
    print("TOP 15 HIGHEST SINGLE-ACTION GAINS")
    print("=" * 90)
    top15 = df.sort_values(by='delta_reward', ascending=False).head(15)
    cols = ['seed', 'day', 'money', 'unlocked_quads', 'num_hands', 'num_plants', 'shed_straw', 'p_straw', 'action_name', 'baseline_reward', 'counterfactual_reward', 'delta_reward']
    print(top15[cols].to_string(index=False))

    print("\n" + "=" * 90)
    print("DETAILED ANATOMY OF THE TOP OUTLIER (+$$102,268)")
    print("=" * 90)
    top1 = df.sort_values(by='delta_reward', ascending=False).iloc[0]
    for k, v in top1.items():
        print(f"  {k:22s} : {v}")

    print("\n" + "=" * 90)
    print("PER-ACTION BREAKDOWN (Counts & Mean Delta for Δ > $500)")
    print("=" * 90)
    pos_df = df[df['delta_reward'] > 500].copy()
    act_grp = pos_df.groupby('action_name')['delta_reward'].agg(['count', 'mean', 'median', 'max']).sort_values(by='count', ascending=False)
    print(act_grp.to_string())

    print("\n" + "=" * 90)
    print("TEMPORAL DISTRIBUTION OF ALPHA (Days 0-25)")
    print("=" * 90)
    pos_df['day_bucket'] = pd.cut(pos_df['day'], bins=[-1, 3, 7, 11, 15, 20, 30], labels=['Day 0-3', 'Day 4-7', 'Day 8-11', 'Day 12-15', 'Day 16-20', 'Day 21+'])
    day_grp = pos_df.groupby('day_bucket', observed=True)['delta_reward'].agg(['count', 'mean', 'median', 'max'])
    print(day_grp.to_string())

if __name__ == "__main__":
    audit()
