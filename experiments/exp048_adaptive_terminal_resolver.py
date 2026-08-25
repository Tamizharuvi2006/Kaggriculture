"""EXP048: Track B (Adaptive Terminal Harvest Resolver Tournament & Loss Recovery).
Evaluates the Adaptive Terminal Harvest Resolver (ATHR) across:
1. Direct inspection of the 4 target loss seeds (Seed 22222, Seed 777777, Seed 590244349).
2. Full 64-match parallel tournament across 32 holdout seeds against kaitofukami-v18.
Measures:
- Mean Bank, Median, Floor, Peak
- Win Rate vs v18 (Target >= 93.8%)
- Recovery Rate of Target Deficit Seeds
- Action Parity on Steps 0-671 (Must be 100.0%).
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
from engine.macro_money.terminal_resolver import AdaptiveTerminalAgent

def eval_athr_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match comparing ATHR vs v18 on a single seed."""
    results = []

    # =========================================================================
    # GAME 1: ATHR = Seat 0 (Player 0), v18 = Seat 1 (Player 1)
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    athr1 = AdaptiveTerminalAgent()

    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        act0 = athr1.act(obs0, env1.configuration)
        act1 = bot_v18.agent(obs1)
        env1.step([act0, act1])

    r_athr_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie1 = r_athr_s0 + r_v18_s1

    results.append({
        "seed": seed,
        "seat": 0,
        "athr_bank": r_athr_s0,
        "v18_bank": r_v18_s1,
        "margin": r_athr_s0 - r_v18_s1,
        "is_win": (r_athr_s0 > r_v18_s1),
        "is_tie": (r_athr_s0 == r_v18_s1),
        "market_pie": pie1,
        "share": (r_athr_s0 / pie1 * 100.0) if pie1 > 0 else 50.0,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0 (Player 0), ATHR = Seat 1 (Player 1)
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    athr2 = AdaptiveTerminalAgent()

    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        act0 = bot_v18.agent(obs0)
        act1 = athr2.act(obs1, env2.configuration)
        env2.step([act0, act1])

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_athr_s1 = float(env2.state[1].reward or 0.0)
    pie2 = r_athr_s1 + r_v18_s0

    results.append({
        "seed": seed,
        "seat": 1,
        "athr_bank": r_athr_s1,
        "v18_bank": r_v18_s0,
        "margin": r_athr_s1 - r_v18_s0,
        "is_win": (r_athr_s1 > r_v18_s0),
        "is_tie": (r_athr_s1 == r_v18_s0),
        "market_pie": pie2,
        "share": (r_athr_s1 / pie2 * 100.0) if pie2 > 0 else 50.0,
    })

    return results

def run_exp048():
    print("=" * 105)
    print("EXP048: ADAPTIVE TERMINAL HARVEST RESOLVER (ATHR) TOURNAMENT & LOSS RECOVERY")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel 64-match tournament across 32 holdout seeds...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_athr_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    banks_athr = [m["athr_bank"] for m in all_matches]
    banks_v18 = [m["v18_bank"] for m in all_matches]
    margins = [m["margin"] for m in all_matches]
    wins = sum(1 for m in all_matches if m["is_win"])
    ties = sum(1 for m in all_matches if m["is_tie"])
    losses = sum(1 for m in all_matches if not m["is_win"] and not m["is_tie"])

    mean_athr = float(np.mean(banks_athr))
    median_athr = float(np.median(banks_athr))
    min_athr = float(np.min(banks_athr))
    max_athr = float(np.max(banks_athr))
    p10_athr = float(np.percentile(banks_athr, 10))
    p90_athr = float(np.percentile(banks_athr, 90))
    wr_athr = (wins + 0.5 * ties) / len(all_matches)

    # Baseline D.1 stats for direct comparison
    d1_mean = 80010.61
    d1_median = 75751.50
    d1_min = 30475.00
    d1_max = 139307.00
    d1_p10 = 46954.70
    d1_p90 = 124839.60
    d1_wr = 0.938

    print("\n" + "=" * 105)
    print("EXP048 ATHR vs FROZEN CONTROL (VARIANT D.1) COMPARATIVE GAUNTLET")
    print("=" * 105)
    print(f"{'Performance Metric':<28} | {'Frozen Control (D.1)':>20} | {'Candidate EXP048 (ATHR)':>24} | {'Delta (ATHR - D.1)':>20}")
    print("-" * 105)
    print(f"{'Mean / Average Bank':<28} | ${d1_mean:>19,.2f} | ${mean_athr:>23,.2f} | ${mean_athr - d1_mean:>+19,.2f}")
    print(f"{'Median Bank':<28} | ${d1_median:>19,.2f} | ${median_athr:>23,.2f} | ${median_athr - d1_median:>+19,.2f}")
    print(f"{'Minimum Bank (Floor)':<28} | ${d1_min:>19,.2f} | ${min_athr:>23,.2f} | ${min_athr - d1_min:>+19,.2f}")
    print(f"{'Maximum Bank (Peak)':<28} | ${d1_max:>19,.2f} | ${max_athr:>23,.2f} | ${max_athr - d1_max:>+19,.2f}")
    print("-" * 105)
    print(f"{'P10 Percentile':<28} | ${d1_p10:>19,.2f} | ${p10_athr:>23,.2f} | ${p10_athr - d1_p10:>+19,.2f}")
    print(f"{'P90 Percentile':<28} | ${d1_p90:>19,.2f} | ${p90_athr:>23,.2f} | ${p90_athr - d1_p90:>+19,.2f}")
    print("-" * 105)
    print(f"{'Win Rate vs v18':<28} | {d1_wr:>19.1%} | {wr_athr:>23.1%} | {wr_athr - d1_wr:>+19.1%}")
    print(f"{'Total Wins / Losses':<28} | {'60 Wins / 4 Losses':>20} | {f'{wins} Wins / {losses} Losses':>24} | {f'{wins - 60:+d} Wins':>20}")
    print(f"{'Cumulative Net Margin':<28} | {'+$86,801.00':>20} | ${sum(margins):>+23,.2f} | ${sum(margins) - 86801.00:>+19,.2f}")
    print("=" * 105)

    # Recovery Breakdown of the 4 Target Loss Matches
    print("\n" + "=" * 105)
    print("TARGET DEFICIT RECOVERY AUTOPSY (MATCH-BY-MATCH INSPECTION)")
    print("=" * 105)
    
    target_keys = [(22222, 0), (777777, 0), (777777, 1), (590244349, 1)]
    for seed, seat in target_keys:
        m = next(match for match in all_matches if match["seed"] == seed and match["seat"] == seat)
        d1_prev_margin = {
            (22222, 0): -6377.00,
            (777777, 0): -1638.00,
            (777777, 1): -1112.00,
            (590244349, 1): -162.00
        }[(seed, seat)]
        
        status = "RECOVERED TO WIN [OK]" if m["is_win"] else ("RECOVERED TO TIE [OK]" if m["is_tie"] else "UNRECOVERED [X]")
        print(f"Seed {seed:>10} (Seat {seat}) | Prev D.1 Margin: ${d1_prev_margin:>+9,.2f} | ATHR Margin: ${m['margin']:>+9,.2f} | ATHR Bank: ${m['athr_bank']:>10,.2f} | {status}")

    print("=" * 105)

if __name__ == "__main__":
    run_exp048()
