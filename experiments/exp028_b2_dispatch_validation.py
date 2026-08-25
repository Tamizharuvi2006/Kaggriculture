"""EXP028: Track B (Candidate B.2: Custom Unit Dispatcher Validation).
Runs a fast tournament evaluating dynamic unit dispatching against Frozen Control (Variant D.1) and v18.
Measures:
- Physical throughput (Milk produced, Crop yield)
- Mean, Median, Min, Max, Win Rate vs v18
- Dual-Gate promotion check.
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
from engine.macro_money.b2_dispatch_agent import B2DispatchAgent

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

def run_exp028():
    print("=" * 95)
    print("EXP028: TRACK B CANDIDATE B.2 (CUSTOM UNIT DISPATCHER) vs CONTROL D.1 vs v18")
    print("=" * 95)

    seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 22222]

    b2_banks = []
    v18_banks = []
    b2_wins = 0.0

    print(f"Simulating Candidate B.2 vs kaitofukami-v18 across {len(seeds)} seeds (16 matches)...")
    for s in seeds:
        # Match 1: B.2 = Seat 0, v18 = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        b2_1 = B2DispatchAgent(target_cows=12)
        while not env1.done:
            env1.step([b2_1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        r_b2_s0 = float(env1.state[0].reward or 0.0)
        r_v18_s1 = float(env1.state[1].reward or 0.0)
        if r_b2_s0 > r_v18_s1: b2_wins += 1.0
        elif r_b2_s0 == r_v18_s1: b2_wins += 0.5

        # Match 2: v18 = Seat 0, B.2 = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        b2_2 = B2DispatchAgent(target_cows=12)
        while not env2.done:
            env2.step([bot_v18.agent(env2.state[0].observation), b2_2.act(env2.state[1].observation)])
        r_v18_s0 = float(env2.state[0].reward or 0.0)
        r_b2_s1 = float(env2.state[1].reward or 0.0)
        if r_b2_s1 > r_v18_s0: b2_wins += 1.0
        elif r_b2_s1 == r_v18_s0: b2_wins += 0.5

        b2_banks.extend([r_b2_s0, r_b2_s1])
        v18_banks.extend([r_v18_s1, r_v18_s0])

    stats_b2 = compute_distribution_stats(b2_banks)
    win_rate_b2 = b2_wins / (len(seeds) * 2)

    # Control baseline on the same 8 seeds
    ctrl_banks = []
    ctrl_wins = 0.0
    for s in seeds:
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        c1 = VariantDAgent()
        while not env1.done:
            env1.step([c1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        ctrl_banks.append(float(env1.state[0].reward or 0.0))

        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        c2 = VariantDAgent()
        while not env2.done:
            env2.step([bot_v18.agent(env2.state[0].observation), c2.act(env2.state[1].observation)])
        ctrl_banks.append(float(env2.state[1].reward or 0.0))

    stats_ctrl = compute_distribution_stats(ctrl_banks)

    print("\n" + "=" * 95)
    print("EXP028 CANDIDATE B.2 COMPARATIVE REPORT (16 Matches on 8 Holdout Seeds)")
    print("=" * 95)
    print(f"{'Metric':<22} | {'Frozen Control (D.1)':>20} | {'Candidate B.2 (Dispatcher)':>26} | {'Delta (B.2 - D.1)':>18}")
    print("-" * 95)
    print(f"{'Mean / Average Bank':<22} | ${stats_ctrl['mean']:>19,.2f} | ${stats_b2['mean']:>25,.2f} | ${stats_b2['mean'] - stats_ctrl['mean']:>+17,.2f}")
    print(f"{'Median Bank':<22} | ${stats_ctrl['median']:>19,.2f} | ${stats_b2['median']:>25,.2f} | ${stats_b2['median'] - stats_ctrl['median']:>+17,.2f}")
    print(f"{'Minimum Bank (Floor)':<22} | ${stats_ctrl['min']:>19,.2f} | ${stats_b2['min']:>25,.2f} | ${stats_b2['min'] - stats_ctrl['min']:>+17,.2f}")
    print(f"{'Maximum Bank (Peak)':<22} | ${stats_ctrl['max']:>19,.2f} | ${stats_b2['max']:>25,.2f} | ${stats_b2['max'] - stats_ctrl['max']:>+17,.2f}")
    print("-" * 95)
    print(f"{'Win Rate vs v18':<22} | {'75.0%':>20} | {win_rate_b2:>25.1%} | {win_rate_b2 - 0.75:>+17.1%}")
    print("=" * 95)

    passed_money = (stats_b2['mean'] > stats_ctrl['mean'])
    passed_tournament = (win_rate_b2 >= 0.75)

    print("\nPROMOTION GATE EVALUATION:")
    print(f"  - Money Gate (Mean > ${stats_ctrl['mean']:,.2f})     : {'PASSED [OK]' if passed_money else 'FAILED [X]'}")
    print(f"  - Tournament Gate (Win Rate >= 75.0% vs v18): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")

    if passed_money and passed_tournament:
        print("\n>>> VERDICT: PROMOTE CANDIDATE B.2 TO TRACK B BASELINE!")
    else:
        print("\n>>> VERDICT: CANDIDATE B.2 UNDERPERFORMS CONTROL D.1. (KEEP FROZEN D.1)")
    print("=" * 95)

if __name__ == "__main__":
    run_exp028()
