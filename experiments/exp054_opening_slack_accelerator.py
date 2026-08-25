"""EXP054: Track B (Opening Slack Accelerator Tournament & Delta Efficacy).
Evaluates the Opening Slack Accelerator (OSA) across:
1. Gate 1: Reachability & Safety Gate on Seed 42 (Measures pre-tilled plot count and Day 0-4 divergence).
2. Gate 2: Full 64-Match Parallel Tournament across 32 Holdout Seeds vs kaitofukami-v18.
Measures:
- Mean Bank Delta vs Control D.1 ($80,010.61)
- Win Rate vs v18 (Target >= 93.8%)
- Total Opening Idle Steps Converted into Productive Pre-Tilling
- Wealth Delta per Idle Step Converted ($/step).
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
from engine.macro_money.opening_slack_accelerator import OpeningSlackAgent
from engine.evaluation.reachability_gate import verify_reachability

def eval_exp054_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match comparing OSA vs v18 on a single seed."""
    results = []

    # =========================================================================
    # GAME 1: OSA = Seat 0, v18 = Seat 1
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    osa1 = OpeningSlackAgent()

    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        act0 = osa1.act(obs0, env1.configuration)
        act1 = bot_v18.agent(obs1)
        env1.step([act0, act1])

    r_osa_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie1 = r_osa_s0 + r_v18_s1

    results.append({
        "seed": seed,
        "seat": 0,
        "osa_bank": r_osa_s0,
        "v18_bank": r_v18_s1,
        "margin": r_osa_s0 - r_v18_s1,
        "is_win": (r_osa_s0 > r_v18_s1),
        "is_tie": (r_osa_s0 == r_v18_s1),
        "market_pie": pie1,
        "idle_converted": osa1.osa.idle_steps_converted,
        "pre_tilled": osa1.osa.pre_tilled_count,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0, OSA = Seat 1
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    osa2 = OpeningSlackAgent()

    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        act0 = bot_v18.agent(obs0)
        act1 = osa2.act(obs1, env2.configuration)
        env2.step([act0, act1])

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_osa_s1 = float(env2.state[1].reward or 0.0)
    pie2 = r_osa_s1 + r_v18_s0

    results.append({
        "seed": seed,
        "seat": 1,
        "osa_bank": r_osa_s1,
        "v18_bank": r_v18_s0,
        "margin": r_osa_s1 - r_v18_s0,
        "is_win": (r_osa_s1 > r_v18_s0),
        "is_tie": (r_osa_s1 == r_v18_s0),
        "market_pie": pie2,
        "idle_converted": osa2.osa.idle_steps_converted,
        "pre_tilled": osa2.osa.pre_tilled_count,
    })

    return results

def run_exp054():
    print("=" * 105)
    print("EXP054: OPENING SLACK ACCELERATOR (OSA) TOURNAMENT & EFFICACY GAUNTLET")
    print("=" * 105)

    # Step 1: Reachability Gate on Seed 42
    print("--- STEP 1: REACHABILITY GATE (Seed 42) ---")
    osa_candidate = OpeningSlackAgent()
    passed, r_info = verify_reachability(osa_candidate.act, "Opening Slack Accelerator (OSA)", seed=42)
    print(f"  [REACHABILITY] Divergence: {r_info['action_divergence_pct']:.1f}% | Gate Status: {'PASSED [OK]' if passed else 'FAILED [X]'}")

    # Step 2: Full 64-Match Tournament across 32 holdout seeds
    print("\n--- STEP 2: FULL 64-MATCH HOLDOUT TOURNAMENT (32 SEEDS, BOTH SEATS) ---")
    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_exp054_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    banks = [m["osa_bank"] for m in all_matches]
    margins = [m["margin"] for m in all_matches]
    wins = sum(1 for m in all_matches if m["is_win"])
    ties = sum(1 for m in all_matches if m["is_tie"])
    losses = sum(1 for m in all_matches if not m["is_win"] and not m["is_tie"])

    mean_osa = float(np.mean(banks))
    median_osa = float(np.median(banks))
    min_osa = float(np.min(banks))
    max_osa = float(np.max(banks))
    p10_osa = float(np.percentile(banks, 10))
    p90_osa = float(np.percentile(banks, 90))
    wr_osa = (wins + 0.5 * ties) / len(all_matches)

    tot_idle_converted = sum(m["idle_converted"] for m in all_matches)
    avg_idle_converted = tot_idle_converted / len(all_matches)

    # D.1 Baseline comparison
    d1_mean = 80010.61
    d1_median = 75751.50
    d1_min = 30475.00
    d1_max = 139307.00
    d1_p10 = 46954.70
    d1_p90 = 124839.60
    d1_wr = 0.938

    delta_mean = mean_osa - d1_mean
    dollar_per_step = (delta_mean / avg_idle_converted) if avg_idle_converted > 0 else 0.0

    print("\n" + "=" * 105)
    print("EXP054 OSA vs FROZEN CONTROL (VARIANT D.1) COMPARATIVE GAUNTLET")
    print("=" * 105)
    print(f"{'Performance Metric':<28} | {'Frozen Control (D.1)':>20} | {'Candidate EXP054 (OSA)':>24} | {'Delta (OSA - D.1)':>20}")
    print("-" * 105)
    print(f"{'Mean / Average Bank':<28} | ${d1_mean:>19,.2f} | ${mean_osa:>23,.2f} | ${delta_mean:>+19,.2f}")
    print(f"{'Median Bank':<28} | ${d1_median:>19,.2f} | ${median_osa:>23,.2f} | ${median_osa - d1_median:>+19,.2f}")
    print(f"{'Minimum Bank (Floor)':<28} | ${d1_min:>19,.2f} | ${min_osa:>23,.2f} | ${min_osa - d1_min:>+19,.2f}")
    print(f"{'Maximum Bank (Peak)':<28} | ${d1_max:>19,.2f} | ${max_osa:>23,.2f} | ${max_osa - d1_max:>+19,.2f}")
    print("-" * 105)
    print(f"{'P10 Percentile':<28} | ${d1_p10:>19,.2f} | ${p10_osa:>23,.2f} | ${p10_osa - d1_p10:>+19,.2f}")
    print(f"{'P90 Percentile':<28} | ${d1_p90:>19,.2f} | ${p90_osa:>23,.2f} | ${p90_osa - d1_p90:>+19,.2f}")
    print("-" * 105)
    print(f"{'Win Rate vs v18':<28} | {d1_wr:>19.1%} | {wr_osa:>23.1%} | {wr_osa - d1_wr:>+19.1%}")
    print(f"{'Total Wins / Losses':<28} | {'60 Wins / 4 Losses':>20} | {f'{wins} Wins / {losses} Losses':>24} | {f'{wins - 60:+d} Wins':>20}")
    print(f"{'Cumulative Net Margin':<28} | {'+$86,801.00':>20} | ${sum(margins):>+23,.2f} | ${sum(margins) - 86801.00:>+19,.2f}")
    print("=" * 105)

    print("\n" + "=" * 105)
    print("OPENING SLACK CONVERSION EFFICIENCY METRICS")
    print("=" * 105)
    print(f"  - Average Opening Idle Steps Converted   : {avg_idle_converted:.1f} steps/game (out of ~115 total idle steps)")
    print(f"  - Total Pre-Tilled Plots Generated       : {sum(m['pre_tilled'] for m in all_matches) / len(all_matches):.1f} plots/game")
    print(f"  - Wealth Delta per Converted Idle Step   : ${dollar_per_step:+.2f} per worker-step")
    print("=" * 105)

    passed_tournament = (wr_osa >= 0.938)
    improved_mean = (mean_osa >= d1_mean + 100.0)

    print("\nPROMOTION EVALUATION:")
    print(f"  - Reachability Gate Status            : {'PASSED [OK]' if passed else 'FAILED [X]'}")
    print(f"  - Tournament Gate (Win Rate >= 93.8%): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")
    print(f"  - Positive Alpha Delta Check          : {'POSITIVE ALPHA [OK]' if improved_mean else 'NEUTRAL / NEGATIVE [X]'}")

    if passed and passed_tournament and improved_mean:
        print("\n>>> VERDICT: OPENING SLACK ACCELERATOR IS EMPIRICALLY SUPERIOR! PROMOTE TO BASELINE!")
    else:
        print("\n>>> VERDICT: OSA DOES NOT EXCEED FROZEN D.1. (KEEP FROZEN D.1)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp054()
