"""EXP120: Seed-Regime Causality Analysis.

Investigates whether the 1200+ rating wall is caused by encountering particular
seed-generated economic regimes rather than by a universally superior opponent strategy.

Uses the 8,268 replay corpus (16,536 seats) to analyze:
1. Seed distribution and correlation with reward
2. Seed bucket vs reward / win rate
3. Seed modulo patterns
4. Cluster-level seed signatures
5. Reward variance explained by seed vs Elo vs agent
"""
import pandas as pd
import numpy as np
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx_path = os.path.join(BASE, "datasets", "il", "index.csv")
clu_path = os.path.join(BASE, "datasets", "il", "clusters.csv")

idx = pd.read_csv(idx_path)
clu = pd.read_csv(clu_path)
merged = pd.merge(clu, idx[['episode_id', 'seed', 'elo_avg', 'reward0', 'reward1', 'winner']], on='episode_id')

print("=" * 120)
print("EXP120: SEED-REGIME CAUSALITY ANALYSIS")
print("=" * 120)

print(f"\nTotal episodes: {len(idx)}")
print(f"Total seats: {len(merged)}")
print(f"Seed range: {merged['seed'].min()} - {merged['seed'].max()}")
print(f"Elo range: {merged['elo_avg'].min():.1f} - {merged['elo_avg'].max():.1f}")

# === 1. CORRELATIONS ===
print("\n" + "=" * 120)
print("1. CORRELATION ANALYSIS")
print("=" * 120)
print(f"Corr(seed, reward):       {merged['seed'].corr(merged['reward']):.4f}")
print(f"Corr(seed, reward0):      {merged['seed'].corr(merged['reward0']):.4f}")
print(f"Corr(elo_avg, reward):    {merged['elo_avg'].corr(merged['reward']):.4f}")
print(f"Corr(elo_avg, reward0):   {merged['elo_avg'].corr(merged['reward0']):.4f}")

merged['log_seed'] = np.log10(merged['seed'] + 1)
print(f"Corr(log_seed, reward):   {merged['log_seed'].corr(merged['reward']):.4f}")

# === 2. SEED BUCKETS ===
print("\n" + "=" * 120)
print("2. SEED BUCKET vs REWARD / WIN RATE")
print("=" * 120)
merged['seed_bucket'] = pd.cut(merged['seed'], bins=[0, 1e6, 1e7, 1e8, 1e9, 2.2e9],
                               labels=['0-1M', '1M-10M', '10M-100M', '100M-1B', '1B+'])
print(f"{'Bucket':<12s} | {'N':>6s} | {'AvgR':>10s} | {'StdR':>10s} | {'MinR':>10s} | {'MaxR':>10s} | {'WR%':>6s}")
print("-" * 80)
for bucket, grp in merged.groupby('seed_bucket'):
    wr = grp['won'].mean() * 100
    print(f"{str(bucket):<12s} | {len(grp):6d} | {grp['reward'].mean():10.0f} | {grp['reward'].std():10.0f} | {grp['reward'].min():10.0f} | {grp['reward'].max():10.0f} | {wr:5.1f}%")

# === 3. SEED MODULO ===
print("\n" + "=" * 120)
print("3. SEED MODULO ANALYSIS")
print("=" * 120)
for mod_val in [100, 500, 1000, 5000, 10000]:
    merged[f'seed_mod_{mod_val}'] = merged['seed'] % mod_val
    corr = merged[f'seed_mod_{mod_val}'].corr(merged['reward'])
    print(f"seed % {mod_val:>5d} -> corr with reward: {corr:+.4f}")

print()
print(f"{'seed%1000 bucket':<20s} | {'N':>6s} | {'AvgR':>10s} | {'WR%':>6s}")
print("-" * 50)
for lo in range(0, 1000, 200):
    grp = merged[(merged['seed_mod_1000'] >= lo) & (merged['seed_mod_1000'] < lo + 200)]
    if len(grp) > 0:
        print(f"[{lo:3d},{lo+200:3d})         | {len(grp):6d} | {grp['reward'].mean():10.0f} | {grp['won'].mean()*100:5.1f}%")

# === 4. CLUSTER-LEVEL SEED STATS ===
print("\n" + "=" * 120)
print("4. CLUSTER-LEVEL SEED STATISTICS (clusters with N >= 50)")
print("=" * 120)
print(f"{'Cluster':>8s} | {'N':>6s} | {'AvgR':>10s} | {'StdR':>10s} | {'MinR':>10s} | {'MaxR':>10s} | {'WR%':>6s} | {'AvgSeed':>14s} | {'StdSeed':>14s}")
print("-" * 110)
for c_id, grp in merged.groupby('cluster'):
    if len(grp) < 50:
        continue
    wr = grp['won'].mean() * 100
    avg_s = grp['seed'].mean()
    std_s = grp['seed'].std()
    print(f"{c_id:8d} | {len(grp):6d} | {grp['reward'].mean():10.0f} | {grp['reward'].std():10.0f} | {grp['reward'].min():10.0f} | {grp['reward'].max():10.0f} | {wr:5.1f}% | {avg_s:14.0f} | {std_s:14.0f}")

# === 5. REWARD VARIANCE DECOMPOSITION (ETA-SQUARED) ===
print("\n" + "=" * 120)
print("5. REWARD VARIANCE DECOMPOSITION (ETA-SQUARED)")
print("=" * 120)
total_var = merged['reward'].var()

eta2_seed = 0
for bucket, grp in merged.groupby('seed_bucket'):
    eta2_seed += len(grp) * (grp['reward'].mean() - merged['reward'].mean())**2
eta2_seed /= (len(merged) * total_var)
print(f"Eta-squared (seed_bucket):     {eta2_seed:.4f}  ({eta2_seed*100:.2f}% of variance)")

eta2_cluster = 0
for c_id, grp in merged.groupby('cluster'):
    eta2_cluster += len(grp) * (grp['reward'].mean() - merged['reward'].mean())**2
eta2_cluster /= (len(merged) * total_var)
print(f"Eta-squared (cluster):         {eta2_cluster:.4f}  ({eta2_cluster*100:.2f}% of variance)")

merged['elo_quartile'] = pd.qcut(merged['elo_avg'], 4, labels=['Q1','Q2','Q3','Q4'])
eta2_elo = 0
for q, grp in merged.groupby('elo_quartile'):
    eta2_elo += len(grp) * (grp['reward'].mean() - merged['reward'].mean())**2
eta2_elo /= (len(merged) * total_var)
print(f"Eta-squared (elo_quartile):    {eta2_elo:.4f}  ({eta2_elo*100:.2f}% of variance)")

eta2_agent = 0
for a, grp in merged.groupby('agent'):
    eta2_agent += len(grp) * (grp['reward'].mean() - merged['reward'].mean())**2
eta2_agent /= (len(merged) * total_var)
print(f"Eta-squared (agent):           {eta2_agent:.4f}  ({eta2_agent*100:.2f}% of variance)")

# === 6. REWARD DISTRIBUTION QUARTILES ===
print("\n" + "=" * 120)
print("6. REWARD DISTRIBUTION")
print("=" * 120)
for label, q in [('p05', 0.05), ('p10', 0.10), ('p25', 0.25), ('p50', 0.50), ('p75', 0.75), ('p90', 0.90), ('p95', 0.95)]:
    print(f"  {label}: {merged['reward'].quantile(q):10.0f}")

# === 7. HIGH vs LOW REWARD SEED SIGNATURES ===
print("\n" + "=" * 120)
print("7. HIGH vs LOW REWARD SEED SIGNATURES")
print("=" * 120)
p25 = merged['reward'].quantile(0.25)
p75 = merged['reward'].quantile(0.75)
low = merged[merged['reward'] <= p25]
high = merged[merged['reward'] >= p75]

print(f"Low reward (<= p25={p25:.0f}):  N={len(low)}")
print(f"  Seed mean: {low['seed'].mean():.0f}  median: {low['seed'].median():.0f}")
print(f"  Elo mean:  {low['elo_avg'].mean():.1f}")
print(f"  Avg reward: {low['reward'].mean():.0f}")
print(f"High reward (>= p75={p75:.0f}): N={len(high)}")
print(f"  Seed mean: {high['seed'].mean():.0f}  median: {high['seed'].median():.0f}")
print(f"  Elo mean:  {high['elo_avg'].mean():.1f}")
print(f"  Avg reward: {high['reward'].mean():.0f}")

print()
print("=== SEED FIRST DIGIT (BENFORD-STYLE) ===")
merged['seed_first_digit'] = merged['seed'].astype(str).str[0].astype(int)
for d in range(1, 10):
    grp = merged[merged['seed_first_digit'] == d]
    if len(grp) > 0:
        print(f"  First digit {d}: N={len(grp):5d}  AvgR={grp['reward'].mean():8.0f}  WR={grp['won'].mean()*100:5.1f}%")

print()
print("=== SEED PARITY ===")
merged['seed_even'] = merged['seed'] % 2 == 0
for label, grp in merged.groupby('seed_even'):
    parity = 'Even' if label else 'Odd'
    print(f"  {parity} seeds: N={len(grp):5d}  AvgR={grp['reward'].mean():8.0f}  WR={grp['won'].mean()*100:5.1f}%")

print("\n" + "=" * 120)
print("EXP120: ANALYSIS COMPLETE")
print("=" * 120)
