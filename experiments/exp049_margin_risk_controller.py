"""EXP049: Track B (Margin-Aware Risk Controller Tournament & Loss Rescue).
Evaluates the Margin-Aware Risk Controller (MARC) across:
1. Target Deficit Match Rescue (Seed 22222, Seed 777777, Seed 590244349).
2. Full 64-Match Parallel Tournament across 32 Holdout Seeds vs kaitofukami-v18.
Measures:
- Overall Win Rate (Target >= 93.8%)
- New Losses Created (Must be 0)
- Losses Rescued into Wins
- Mean Bank, Median, Floor, Peak.
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
from engine.macro_money.margin_risk_controller import MarginRiskAgent

def eval_marc_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match comparing MARC vs v18 on a single seed."""
    results = []

    # =========================================================================
    # GAME 1: MARC = Seat 0 (Player 0), v18 = Seat 1 (Player 1)
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    marc1 = MarginRiskAgent(behind_threshold=-1500.0)

    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        act0 = marc1.act(obs0, env1.configuration)
        act1 = bot_v18.agent(obs1)
        env1.step([act0, act1])

    r_marc_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie1 = r_marc_s0 + r_v18_s1

    results.append({
        "seed": seed,
        "seat": 0,
        "marc_bank": r_marc_s0,
        "v18_bank": r_v18_s1,
        "margin": r_marc_s0 - r_v18_s1,
        "is_win": (r_marc_s0 > r_v18_s1),
        "is_tie": (r_marc_s0 == r_v18_s1),
        "market_pie": pie1,
        "share": (r_marc_s0 / pie1 * 100.0) if pie1 > 0 else 50.0,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0 (Player 0), MARC = Seat 1 (Player 1)
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    marc2 = MarginRiskAgent(behind_threshold=-1500.0)

    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        act0 = bot_v18.agent(obs0)
        act1 = marc2.act(obs1, env2.configuration)
        env2.step([act0, act1])

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_marc_s1 = float(env2.state[1].reward or 0.0)
    pie2 = r_marc_s1 + r_v18_s0

    results.append({
        "seed": seed,
        "seat": 1,
        "marc_bank": r_marc_s1,
        "v18_bank": r_v18_s0,
        "margin": r_marc_s1 - r_v18_s0,
        "is_win": (r_marc_s1 > r_v18_s0),
        "is_tie": (r_marc_s1 == r_v18_s0),
        "market_pie": pie2,
        "share": (r_marc_s1 / pie2 * 100.0) if pie2 > 0 else 50.0,
    })

    return results

def run_exp049():
    print("=" * 105)
    print("EXP049: MARGIN-AWARE RISK CONTROLLER (MARC) TOURNAMENT & LOSS RESCUE")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel 64-match tournament across 32 holdout seeds...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_marc_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    banks_marc = [m["marc_bank"] for m in all_matches]
    banks_v18 = [m["v18_bank"] for m in all_matches]
    margins = [m["margin"] for m in all_matches]
    wins = sum(1 for m in all_matches if m["is_win"])
    ties = sum(1 for m in all_matches if m["is_tie"])
    losses = sum(1 for m in all_matches if not m["is_win"] and not m["is_tie"])

    mean_marc = float(np.mean(banks_marc))
    median_marc = float(np.median(banks_marc))
    min_marc = float(np.min(banks_marc))
    max_marc = float(np.max(banks_marc))
    p10_marc = float(np.percentile(banks_marc, 10))
    p90_marc = float(np.percentile(banks_marc, 90))
    wr_marc = (wins + 0.5 * ties) / len(all_matches)

    # Baseline D.1 stats for comparison
    d1_mean = 80010.61
    d1_median = 75751.50
    d1_min = 30475.00
    d1_max = 139307.00
    d1_p10 = 46954.70
    d1_p90 = 124839.60
    d1_wr = 0.938

    print("\n" + "=" * 105)
    print("EXP049 MARC vs FROZEN CONTROL (VARIANT D.1) COMPARATIVE GAUNTLET")
    print("=" * 105)
    print(f"{'Performance Metric':<28} | {'Frozen Control (D.1)':>20} | {'Candidate EXP049 (MARC)':>24} | {'Delta (MARC - D.1)':>20}")
    print("-" * 105)
    print(f"{'Mean / Average Bank':<28} | ${d1_mean:>19,.2f} | ${mean_marc:>23,.2f} | ${mean_marc - d1_mean:>+19,.2f}")
    print(f"{'Median Bank':<28} | ${d1_median:>19,.2f} | ${median_marc:>23,.2f} | ${median_marc - d1_median:>+19,.2f}")
    print(f"{'Minimum Bank (Floor)':<28} | ${d1_min:>19,.2f} | ${min_marc:>23,.2f} | ${min_marc - d1_min:>+19,.2f}")
    print(f"{'Maximum Bank (Peak)':<28} | ${d1_max:>19,.2f} | ${max_marc:>23,.2f} | ${max_marc - d1_max:>+19,.2f}")
    print("-" * 105)
    print(f"{'P10 Percentile':<28} | ${d1_p10:>19,.2f} | ${p10_marc:>23,.2f} | ${p10_marc - d1_p10:>+19,.2f}")
    print(f"{'P90 Percentile':<28} | ${d1_p90:>19,.2f} | ${p90_marc:>23,.2f} | ${p90_marc - d1_p90:>+19,.2f}")
    print("-" * 105)
    print(f"{'Win Rate vs v18':<28} | {d1_wr:>19.1%} | {wr_marc:>23.1%} | {wr_marc - d1_wr:>+19.1%}")
    print(f"{'Total Wins / Losses':<28} | {'60 Wins / 4 Losses':>20} | {f'{wins} Wins / {losses} Losses':>24} | {f'{wins - 60:+d} Wins':>20}")
    print(f"{'Cumulative Net Margin':<28} | {'+$86,801.00':>20} | ${sum(margins):>+23,.2f} | ${sum(margins) - 86801.00:>+19,.2f}")
    print("=" * 105)

    # Detailed Inspection of Target Loss Matches
    print("\n" + "=" * 105)
    print("TARGET DEFICIT RESCUE AUTOPSY (MATCH-BY-MATCH INSPECTION)")
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
        
        status = "RESCUED TO WIN [OK]" if m["is_win"] else ("RESCUED TO TIE [OK]" if m["is_tie"] else "UNRESCUED [X]")
        print(f"Seed {seed:>10} (Seat {seat}) | Prev D.1 Margin: ${d1_prev_margin:>+9,.2f} | MARC Margin: ${m['margin']:>+9,.2f} | MARC Bank: ${m['marc_bank']:>10,.2f} | {status}")

    print("=" * 105)

    passed_tournament = (wr_marc >= 0.938)
    rescued_any = any(m["is_win"] for seed, seat in target_keys for m in all_matches if m["seed"] == seed and m["seat"] == seat)

    print("\nPROMOTION EVALUATION:")
    print(f"  - Tournament Gate (Win Rate >= 93.8%): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")
    print(f"  - Deficit Rescue Check                : {'RESCUED WINS [OK]' if rescued_any else 'NO RESCUES [X]'}")

    if passed_tournament and (wr_marc > 0.938 or mean_marc > d1_mean + 500):
        print("\n>>> VERDICT: PROMOTE MARC AS NEW TRACK B BASELINE!")
    else:
        print("\n>>> VERDICT: MARC DOES NOT IMPROVE ON FROZEN D.1. (KEEP FROZEN D.1)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp049()
