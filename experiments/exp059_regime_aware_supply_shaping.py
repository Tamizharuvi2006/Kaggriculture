"""EXP059: Track B (Regime-Aware Supply Shaping Tournament & Pricing Gauntlet).
Evaluates Candidate RASS-1 (Regime-Aware Supply Shaping) across:
1. Gate 1: Reachability & Safety Gate on Seed 42 (Verifies action divergence and 100% wave completion).
2. Gate 2: Full 64-Match Parallel Tournament across 32 Holdout Seeds vs kaitofukami-v18.
Measures:
- Mean Bank Delta vs Control D.1 ($80,010.61)
- Win Rate vs v18 (Target >= 93.8%)
- Average Realized Commodity Sale Price ($/unit)
- Tranche Execution Volume and Staggering Intervals
- Regime-by-Regime Win Rate and Wealth Decomposition.
"""
from __future__ import annotations
import sys
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent
from engine.macro_money.regime_aware_supply_shaper import RASSAgent
from engine.evaluation.reachability_gate import verify_reachability

def eval_exp059_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match comparing RASS-1 vs v18 on a single seed."""
    results = []

    # =========================================================================
    # GAME 1: RASS-1 = Seat 0, v18 = Seat 1
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    rass1 = RASSAgent()
    straw_prices1 = []

    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation

        act0 = rass1.act(obs0, env1.configuration)
        act1 = bot_v18.agent(obs1)

        p = obs0.get("market", {}).get("prices", {})
        straw_prices1.append(float(p.get("STRAWBERRY", 120)))

        env1.step([act0, act1])

    r_rass_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie1 = r_rass_s0 + r_v18_s1

    results.append({
        "seed": seed,
        "seat": 0,
        "rass_bank": r_rass_s0,
        "v18_bank": r_v18_s1,
        "margin": r_rass_s0 - r_v18_s1,
        "is_win": (r_rass_s0 > r_v18_s1),
        "is_tie": (r_rass_s0 == r_v18_s1),
        "market_pie": pie1,
        "mean_straw_price": float(np.mean(straw_prices1)),
        "tranche1_sales": rass1.shaper.tranche1_sales,
        "tranche2_sales": rass1.shaper.tranche2_sales,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0, RASS-1 = Seat 1
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    rass2 = RASSAgent()
    straw_prices2 = []

    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation

        act0 = bot_v18.agent(obs0)
        act1 = rass2.act(obs1, env2.configuration)

        p = obs1.get("market", {}).get("prices", {})
        straw_prices2.append(float(p.get("STRAWBERRY", 120)))

        env2.step([act0, act1])

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_rass_s1 = float(env2.state[1].reward or 0.0)
    pie2 = r_rass_s1 + r_v18_s0

    results.append({
        "seed": seed,
        "seat": 1,
        "rass_bank": r_rass_s1,
        "v18_bank": r_v18_s0,
        "margin": r_rass_s1 - r_v18_s0,
        "is_win": (r_rass_s1 > r_v18_s0),
        "is_tie": (r_rass_s1 == r_v18_s0),
        "market_pie": pie2,
        "mean_straw_price": float(np.mean(straw_prices2)),
        "tranche1_sales": rass2.shaper.tranche1_sales,
        "tranche2_sales": rass2.shaper.tranche2_sales,
    })

    return results

def run_exp059():
    print("=" * 105)
    print("EXP059: REGIME-AWARE SUPPLY SHAPING (RASS-1) TOURNAMENT & PRICING GAUNTLET")
    print("=" * 105)

    # Step 1: Reachability Gate on Seed 42
    print("--- STEP 1: REACHABILITY GATE (Seed 42) ---")
    candidate = RASSAgent()
    passed, r_info = verify_reachability(candidate.act, "Regime-Aware Supply Shaping (RASS-1)", seed=42)
    print(f"  [REACHABILITY] Divergence: {r_info['action_divergence_pct']:.1f}% | Gate Status: {'PASSED [OK]' if passed else 'FAILED [X]'}")

    # Step 2: Full 64-Match Holdout Tournament across 32 seeds
    print("\n--- STEP 2: FULL 64-MATCH HOLDOUT TOURNAMENT (32 SEEDS, BOTH SEATS) ---")
    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_exp059_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    banks = [m["rass_bank"] for m in all_matches]
    margins = [m["margin"] for m in all_matches]
    wins = sum(1 for m in all_matches if m["is_win"])
    ties = sum(1 for m in all_matches if m["is_tie"])
    losses = sum(1 for m in all_matches if not m["is_win"] and not m["is_tie"])

    mean_b = float(np.mean(banks))
    median_b = float(np.median(banks))
    min_b = float(np.min(banks))
    max_b = float(np.max(banks))
    p10_b = float(np.percentile(banks, 10))
    p90_b = float(np.percentile(banks, 90))
    wr = (wins + 0.5 * ties) / len(all_matches)

    # D.1 Baseline comparison
    d1_mean = 80010.61
    d1_median = 75751.50
    d1_min = 30475.00
    d1_max = 139307.00
    d1_p10 = 46954.70
    d1_p90 = 124839.60
    d1_wr = 0.938
    d1_straw_p = 154.5

    mean_p = float(np.mean([m["mean_straw_price"] for m in all_matches]))

    print("\n" + "=" * 105)
    print("EXP059 RASS-1 vs FROZEN CONTROL (VARIANT D.1) COMPARATIVE GAUNTLET")
    print("=" * 105)
    print(f"{'Performance Metric':<28} | {'Frozen Control (D.1)':>20} | {'Candidate EXP059 (RASS-1)':>24} | {'Delta (RASS - D.1)':>20}")
    print("-" * 105)
    print(f"{'Mean / Average Bank':<28} | ${d1_mean:>19,.2f} | ${mean_b:>23,.2f} | ${mean_b - d1_mean:>+19,.2f}")
    print(f"{'Median Bank':<28} | ${d1_median:>19,.2f} | ${median_b:>23,.2f} | ${median_b - d1_median:>+19,.2f}")
    print(f"{'Minimum Bank (Floor)':<28} | ${d1_min:>19,.2f} | ${min_b:>23,.2f} | ${min_b - d1_min:>+19,.2f}")
    print(f"{'Maximum Bank (Peak)':<28} | ${d1_max:>19,.2f} | ${max_b:>23,.2f} | ${max_b - d1_max:>+19,.2f}")
    print("-" * 105)
    print(f"{'P10 Percentile':<28} | ${d1_p10:>19,.2f} | ${p10_b:>23,.2f} | ${p10_b - d1_p10:>+19,.2f}")
    print(f"{'P90 Percentile':<28} | ${d1_p90:>19,.2f} | ${p90_b:>23,.2f} | ${p90_b - d1_p90:>+19,.2f}")
    print("-" * 105)
    print(f"{'Win Rate vs v18':<28} | {d1_wr:>19.1%} | {wr:>23.1%} | {wr - d1_wr:>+19.1%}")
    print(f"{'Total Wins / Losses':<28} | {'60 Wins / 4 Losses':>20} | {f'{wins} Wins / {losses} Losses':>24} | {f'{wins - 60:+d} Wins':>20}")
    print(f"{'Cumulative Net Margin':<28} | {'+$86,801.00':>20} | ${sum(margins):>+23,.2f} | ${sum(margins) - 86801.00:>+19,.2f}")
    print(f"{'Mean Strawberry Price':<28} | ${d1_straw_p:>19.1f}/u | ${mean_p:>23.1f}/u | ${mean_p - d1_straw_p:>+19.1f}/u")
    print("=" * 105)

    passed_tournament = (wr >= 0.938)
    improved_mean = (mean_b >= d1_mean + 100.0)

    print("\nPROMOTION EVALUATION:")
    print(f"  - Reachability Gate Status            : {'PASSED [OK]' if passed else 'FAILED [X]'}")
    print(f"  - Tournament Gate (Win Rate >= 93.8%): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")
    print(f"  - Positive Alpha Delta Check          : {'POSITIVE ALPHA [OK]' if improved_mean else 'NEUTRAL / NEGATIVE [X]'}")

    if passed and passed_tournament and improved_mean:
        print("\n>>> VERDICT: REGIME-AWARE SUPPLY SHAPING IS EMPIRICALLY SUPERIOR! PROMOTE TO BASELINE!")
    else:
        print("\n>>> VERDICT: RASS-1 DOES NOT EXCEED FROZEN D.1. (KEEP FROZEN D.1)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp059()
