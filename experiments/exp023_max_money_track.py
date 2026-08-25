"""EXP023: Track B Max-Money Challenger Tournament (Target: $150k+ Average Bank).
Executes 64 full 720-step matches across 32 unseen holdout seeds to compare:
- Track B: MaxMoneyAgent (4 Quadrants, 52 Strawberries, 12 Cows, 18 Workers)
- Track A: Variant D.1 Control (3 Quadrants, 38 Strawberries, 8 Cows, 13 Workers)
- Benchmark: kaitofukami-v18
Computes full terminal coin distributions: Mean, Median, Min, Max, P10, P25, P75, P90, Win Rate.
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
from engine.macro_money.agent import MaxMoneyAgent

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

def run_exp023():
    print("=" * 95)
    print("EXP023: TRACK B (MAX-MONEY 4-QUADRANT) vs TRACK A (VARIANT D.1) vs v18")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    track_b_all = []
    v18_all = []
    track_b_wins = 0.0

    print(f"Simulating Track B vs kaitofukami-v18 across {len(seeds)} seeds (64 matches)...")
    for s in seeds:
        # Match 1: Track B = Seat 0, v18 = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        b1 = MaxMoneyAgent()
        while not env1.done:
            obs0 = env1.state[0].observation
            obs1 = env1.state[1].observation
            env1.step([b1.act(obs0), bot_v18.agent(obs1)])
        r_b_s0 = float(env1.state[0].reward or 0.0)
        r_v_s1 = float(env1.state[1].reward or 0.0)
        if r_b_s0 > r_v_s1: track_b_wins += 1.0
        elif r_b_s0 == r_v_s1: track_b_wins += 0.5

        # Match 2: v18 = Seat 0, Track B = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        b2 = MaxMoneyAgent()
        while not env2.done:
            obs0 = env2.state[0].observation
            obs1 = env2.state[1].observation
            env2.step([bot_v18.agent(obs0), b2.act(obs1)])
        r_v_s0 = float(env2.state[0].reward or 0.0)
        r_b_s1 = float(env2.state[1].reward or 0.0)
        if r_b_s1 > r_v_s0: track_b_wins += 1.0
        elif r_b_s1 == r_v_s0: track_b_wins += 0.5

        track_b_all.extend([r_b_s0, r_b_s1])
        v18_all.extend([r_v_s1, r_v_s0])

    stats_b = compute_distribution_stats(track_b_all)
    stats_v = compute_distribution_stats(v18_all)
    win_rate_b = track_b_wins / (len(seeds) * 2)

    # Load Track A (D.1) baseline stats from reports/D1_FINAL_COIN_DISTRIBUTION.json
    with open(os.path.join(BASE_DIR, "reports", "D1_FINAL_COIN_DISTRIBUTION.json"), "r") as f:
        d1_data = json.load(f)
    stats_a = d1_data["overall_cand"]

    print("\n" + "=" * 95)
    print("EXP023 COMPARATIVE TERMINAL COIN REPORT (64 MATCHES / 32 SEEDS)")
    print("=" * 95)
    print(f"{'Metric':<22} | {'Track A (Variant D.1)':>20} | {'Track B (MaxMoneyAgent)':>23} | {'Delta (B - A)':>18}")
    print("-" * 92)
    print(f"{'Mean / Average Bank':<22} | ${stats_a['mean']:>19,.2f} | ${stats_b['mean']:>22,.2f} | ${stats_b['mean'] - stats_a['mean']:>+17,.2f}")
    print(f"{'Median Bank':<22} | ${stats_a['median']:>19,.2f} | ${stats_b['median']:>22,.2f} | ${stats_b['median'] - stats_a['median']:>+17,.2f}")
    print(f"{'Minimum Bank (Floor)':<22} | ${stats_a['min']:>19,.2f} | ${stats_b['min']:>22,.2f} | ${stats_b['min'] - stats_a['min']:>+17,.2f}")
    print(f"{'Maximum Bank (Peak)':<22} | ${stats_a['max']:>19,.2f} | ${stats_b['max']:>22,.2f} | ${stats_b['max'] - stats_a['max']:>+17,.2f}")
    print(f"{'Standard Deviation':<22} | ${stats_a['std']:>19,.2f} | ${stats_b['std']:>22,.2f} | ${stats_b['std'] - stats_a['std']:>+17,.2f}")
    print("-" * 92)
    print(f"{'P10 Percentile':<22} | ${stats_a['p10']:>19,.2f} | ${stats_b['p10']:>22,.2f} | ${stats_b['p10'] - stats_a['p10']:>+17,.2f}")
    print(f"{'P25 Percentile':<22} | ${stats_a['p25']:>19,.2f} | ${stats_b['p25']:>22,.2f} | ${stats_b['p25'] - stats_a['p25']:>+17,.2f}")
    print(f"{'P75 Percentile':<22} | ${stats_a['p75']:>19,.2f} | ${stats_b['p75']:>22,.2f} | ${stats_b['p75'] - stats_a['p75']:>+17,.2f}")
    print(f"{'P90 Percentile':<22} | ${stats_a['p90']:>19,.2f} | ${stats_b['p90']:>22,.2f} | ${stats_b['p90'] - stats_a['p90']:>+17,.2f}")
    print("-" * 92)
    print(f"{'Win Rate vs v18':<22} | {'90.6%':>20} | {win_rate_b:>22.1%} | {win_rate_b - 0.906:>+17.1%}")
    print("=" * 95)

if __name__ == "__main__":
    run_exp023()
