"""EXP022: Ground-Truth Terminal Coin Distribution Report (Variant D.1 vs kaitofukami-v18).
Executes 64 full 720-step matches across 32 unseen holdout seeds to record actual final coin banks.
Computes:
- Total, Mean, Median, Min, Max, StdDev
- P10, P25, P75, P90 percentiles
- Seat 0 vs Seat 1 splits for both Candidate and Opponent
- Raw per-match CSV/JSON logging
"""
from __future__ import annotations
import sys
import os
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent

def compute_distribution_stats(values: list[float]) -> dict[str, float]:
    arr = np.array(values, dtype=np.float64)
    return {
        "count": len(arr),
        "total": float(np.sum(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
    }

def run_distribution_experiment():
    print("=" * 95)
    print("EXP022: GROUND-TRUTH TERMINAL COIN DISTRIBUTION REPORT (64 MATCHES / 32 SEEDS)")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    records = []
    
    cand_all = []
    opp_all = []
    
    cand_seat0 = []
    opp_seat1 = []
    
    cand_seat1 = []
    opp_seat0 = []

    paired_deltas = []

    for idx, seed in enumerate(seeds, 1):
        # Match 1: Candidate = Seat 0, Opponent = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env1.reset()
        cand1 = VariantDAgent()
        while not env1.done:
            obs0 = env1.state[0].observation
            obs1 = env1.state[1].observation
            act0 = cand1.act(obs0)
            act1 = bot_v18.agent(obs1)
            env1.step([act0, act1])
            
        c_m1 = float(env1.state[0].reward or 0.0)
        o_m1 = float(env1.state[1].reward or 0.0)

        # Match 2: Opponent = Seat 0, Candidate = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env2.reset()
        cand2 = VariantDAgent()
        while not env2.done:
            obs0 = env2.state[0].observation
            obs1 = env2.state[1].observation
            act0 = bot_v18.agent(obs0)
            act1 = cand2.act(obs1)
            env2.step([act0, act1])

        o_m2 = float(env2.state[0].reward or 0.0)
        c_m2 = float(env2.state[1].reward or 0.0)

        # Accumulate
        cand_all.extend([c_m1, c_m2])
        opp_all.extend([o_m1, o_m2])
        
        cand_seat0.append(c_m1)
        opp_seat1.append(o_m1)
        
        cand_seat1.append(c_m2)
        opp_seat0.append(o_m2)

        pair_delta = (c_m1 + c_m2) - (o_m1 + o_m2)
        paired_deltas.append(pair_delta)

        records.append({
            "seed": seed,
            "match1": {"seat0_cand": c_m1, "seat1_opp": o_m1, "delta": c_m1 - o_m1, "cand_win": c_m1 > o_m1},
            "match2": {"seat0_opp": o_m2, "seat1_cand": c_m2, "delta": c_m2 - o_m2, "cand_win": c_m2 > o_m2},
            "paired_cand_total": c_m1 + c_m2,
            "paired_opp_total": o_m1 + o_m2,
            "paired_delta": pair_delta,
        })

    # Compute Statistics
    stats_cand_all = compute_distribution_stats(cand_all)
    stats_opp_all = compute_distribution_stats(opp_all)
    
    stats_cand_s0 = compute_distribution_stats(cand_seat0)
    stats_opp_s0 = compute_distribution_stats(opp_seat0)
    
    stats_cand_s1 = compute_distribution_stats(cand_seat1)
    stats_opp_s1 = compute_distribution_stats(opp_seat1)

    mean_paired_margin = float(np.mean(paired_deltas))
    mean_coin_diff = stats_cand_all["mean"] - stats_opp_all["mean"]

    # Save to file
    out_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "D1_FINAL_COIN_DISTRIBUTION.json")
    with open(out_file, "w") as f:
        json.dump({
            "overall_cand": stats_cand_all,
            "overall_opp": stats_opp_all,
            "seat0_cand": stats_cand_s0,
            "seat0_opp": stats_opp_s0,
            "seat1_cand": stats_cand_s1,
            "seat1_opp": stats_opp_s1,
            "mean_paired_margin": mean_paired_margin,
            "mean_coin_difference": mean_coin_diff,
            "per_seed_records": records,
        }, f, indent=2)

    # Print Formatted Report
    print("\n" + "=" * 95)
    print("1. OVERALL TERMINAL COIN SUMMARY (All 64 Matches)")
    print("=" * 95)
    print(f"{'Statistic':<22} | {'Candidate (Variant D.1)':>25} | {'Opponent (v18)':>25}")
    print("-" * 78)
    print(f"{'Total Coins (64 games)':<22} | ${stats_cand_all['total']:>24,.2f} | ${stats_opp_all['total']:>24,.2f}")
    print(f"{'Mean / Average Bank':<22} | ${stats_cand_all['mean']:>24,.2f} | ${stats_opp_all['mean']:>24,.2f}")
    print(f"{'Median Bank':<22} | ${stats_cand_all['median']:>24,.2f} | ${stats_opp_all['median']:>24,.2f}")
    print(f"{'Standard Deviation':<22} | ${stats_cand_all['std']:>24,.2f} | ${stats_opp_all['std']:>24,.2f}")
    print(f"{'Minimum Bank':<22} | ${stats_cand_all['min']:>24,.2f} | ${stats_opp_all['min']:>24,.2f}")
    print(f"{'Maximum Bank':<22} | ${stats_cand_all['max']:>24,.2f} | ${stats_opp_all['max']:>24,.2f}")
    print("-" * 78)
    print(f"{'P10 (10th Percentile)':<22} | ${stats_cand_all['p10']:>24,.2f} | ${stats_opp_all['p10']:>24,.2f}")
    print(f"{'P25 (25th Percentile)':<22} | ${stats_cand_all['p25']:>24,.2f} | ${stats_opp_all['p25']:>24,.2f}")
    print(f"{'P75 (75th Percentile)':<22} | ${stats_cand_all['p75']:>24,.2f} | ${stats_opp_all['p75']:>24,.2f}")
    print(f"{'P90 (90th Percentile)':<22} | ${stats_cand_all['p90']:>24,.2f} | ${stats_opp_all['p90']:>24,.2f}")

    print("\n" + "=" * 95)
    print("2. SEAT-SPLIT TERMINAL COIN BREAKDOWN (32 Matches per Seat)")
    print("=" * 95)
    print(f"{'Statistic':<22} | {'Seat 0 Candidate':>18} | {'Seat 0 Opponent':>18} | {'Seat 1 Candidate':>18} | {'Seat 1 Opponent':>18}")
    print("-" * 95)
    print(f"{'Mean Bank':<22} | ${stats_cand_s0['mean']:>17,.2f} | ${stats_opp_s0['mean']:>17,.2f} | ${stats_cand_s1['mean']:>17,.2f} | ${stats_opp_s1['mean']:>17,.2f}")
    print(f"{'Median Bank':<22} | ${stats_cand_s0['median']:>17,.2f} | ${stats_opp_s0['median']:>17,.2f} | ${stats_cand_s1['median']:>17,.2f} | ${stats_opp_s1['median']:>17,.2f}")
    print(f"{'Min Bank':<22} | ${stats_cand_s0['min']:>17,.2f} | ${stats_opp_s0['min']:>17,.2f} | ${stats_cand_s1['min']:>17,.2f} | ${stats_opp_s1['min']:>17,.2f}")
    print(f"{'Max Bank':<22} | ${stats_cand_s0['max']:>17,.2f} | ${stats_opp_s0['max']:>17,.2f} | ${stats_cand_s1['max']:>17,.2f} | ${stats_opp_s1['max']:>17,.2f}")
    print(f"{'StdDev':<22} | ${stats_cand_s0['std']:>17,.2f} | ${stats_opp_s0['std']:>17,.2f} | ${stats_cand_s1['std']:>17,.2f} | ${stats_opp_s1['std']:>17,.2f}")

    print("\n" + "=" * 95)
    print("3. MARGIN & COIN DIFFERENCE COMPARISON")
    print("=" * 95)
    print(f"Mean Per-Game Coin Difference (Cand Mean - Opp Mean): ${mean_coin_diff:>+14,.2f}")
    print(f"Mean Paired Margin Delta (Sum Cand Pair - Sum Opp Pair): ${mean_paired_margin:>+14,.2f}")
    print(f"Total Cumulative Edge across 64 Games                : ${stats_cand_all['total'] - stats_opp_all['total']:>+14,.2f}")
    print(f"Full Distribution Saved To                           : {out_file}")
    print("=" * 95)

if __name__ == "__main__":
    run_distribution_experiment()
