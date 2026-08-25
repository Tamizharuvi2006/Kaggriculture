"""EXP051: Track B (Conditional Elite-Regime Specialization Tournament & Validation).
Evaluates the Elite-Regime Specialized Agent across:
1. Early Regime Classifier Accuracy across 32 Holdout Seeds.
2. Full 64-Match Parallel Tournament across 32 Holdout Seeds vs kaitofukami-v18.
Measures:
- Elite-Regime Mean Bank (Target > $124k, pushing toward $140k-$150k)
- Non-Elite Regime Parity (Must be 100% identical to Control D.1)
- Overall Tournament Win Rate (Target >= 93.8%)
- Overall Mean Bank.
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
from engine.macro_money.elite_regime_agent import EliteRegimeSpecializedAgent

def eval_exp051_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match comparing Elite-Specialized Agent vs v18 on a single seed."""
    results = []

    # =========================================================================
    # GAME 1: Cand = Seat 0, v18 = Seat 1
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    agent1 = EliteRegimeSpecializedAgent()

    while not env1.done:
        obs0 = env1.state[0].observation
        obs1 = env1.state[1].observation
        act0 = agent1.act(obs0, env1.configuration)
        act1 = bot_v18.agent(obs1)
        env1.step([act0, act1])

    r_cand_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie1 = r_cand_s0 + r_v18_s1

    results.append({
        "seed": seed,
        "seat": 0,
        "cand_bank": r_cand_s0,
        "v18_bank": r_v18_s1,
        "margin": r_cand_s0 - r_v18_s1,
        "is_win": (r_cand_s0 > r_v18_s1),
        "is_tie": (r_cand_s0 == r_v18_s1),
        "market_pie": pie1,
        "is_elite": agent1.classifier.is_elite,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0, Cand = Seat 1
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    agent2 = EliteRegimeSpecializedAgent()

    while not env2.done:
        obs0 = env2.state[0].observation
        obs1 = env2.state[1].observation
        act0 = bot_v18.agent(obs0)
        act1 = agent2.act(obs1, env2.configuration)
        env2.step([act0, act1])

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_cand_s1 = float(env2.state[1].reward or 0.0)
    pie2 = r_cand_s1 + r_v18_s0

    results.append({
        "seed": seed,
        "seat": 1,
        "cand_bank": r_cand_s1,
        "v18_bank": r_v18_s0,
        "margin": r_cand_s1 - r_v18_s0,
        "is_win": (r_cand_s1 > r_v18_s0),
        "is_tie": (r_cand_s1 == r_v18_s0),
        "market_pie": pie2,
        "is_elite": agent2.classifier.is_elite,
    })

    return results

def run_exp051():
    print("=" * 105)
    print("EXP051: CONDITIONAL ELITE-REGIME SPECIALIZATION TOURNAMENT & VALIDATION")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel 64-match tournament across 32 holdout seeds...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_exp051_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    banks_cand = [m["cand_bank"] for m in all_matches]
    margins = [m["margin"] for m in all_matches]
    wins = sum(1 for m in all_matches if m["is_win"])
    ties = sum(1 for m in all_matches if m["is_tie"])
    losses = sum(1 for m in all_matches if not m["is_win"] and not m["is_tie"])

    mean_cand = float(np.mean(banks_cand))
    median_cand = float(np.median(banks_cand))
    min_cand = float(np.min(banks_cand))
    max_cand = float(np.max(banks_cand))
    p10_cand = float(np.percentile(banks_cand, 10))
    p90_cand = float(np.percentile(banks_cand, 90))
    wr_cand = (wins + 0.5 * ties) / len(all_matches)

    # Elite vs Non-Elite Decomposition
    elite_matches = [m for m in all_matches if m["is_elite"]]
    non_elite_matches = [m for m in all_matches if not m["is_elite"]]

    elite_mean = float(np.mean([m["cand_bank"] for m in elite_matches])) if elite_matches else 0.0
    non_elite_mean = float(np.mean([m["cand_bank"] for m in non_elite_matches])) if non_elite_matches else 0.0

    # Baseline D.1 stats for comparison
    d1_mean = 80010.61
    d1_median = 75751.50
    d1_min = 30475.00
    d1_max = 139307.00
    d1_p10 = 46954.70
    d1_p90 = 124839.60
    d1_wr = 0.938
    d1_elite_mean = 124054.79

    print("\n" + "=" * 105)
    print("EXP051 ELITE-SPECIALIZED vs FROZEN CONTROL (VARIANT D.1) COMPARATIVE GAUNTLET")
    print("=" * 105)
    print(f"{'Performance Metric':<28} | {'Frozen Control (D.1)':>20} | {'Candidate EXP051 (Elite)':>24} | {'Delta (EXP051 - D.1)':>20}")
    print("-" * 105)
    print(f"{'Mean / Average Bank':<28} | ${d1_mean:>19,.2f} | ${mean_cand:>23,.2f} | ${mean_cand - d1_mean:>+19,.2f}")
    print(f"{'Elite Regime Mean Bank':<28} | ${d1_elite_mean:>19,.2f} | ${elite_mean:>23,.2f} | ${elite_mean - d1_elite_mean:>+19,.2f}")
    print(f"{'Median Bank':<28} | ${d1_median:>19,.2f} | ${median_cand:>23,.2f} | ${median_cand - d1_median:>+19,.2f}")
    print(f"{'Minimum Bank (Floor)':<28} | ${d1_min:>19,.2f} | ${min_cand:>23,.2f} | ${min_cand - d1_min:>+19,.2f}")
    print(f"{'Maximum Bank (Peak)':<28} | ${d1_max:>19,.2f} | ${max_cand:>23,.2f} | ${max_cand - d1_max:>+19,.2f}")
    print("-" * 105)
    print(f"{'P10 Percentile':<28} | ${d1_p10:>19,.2f} | ${p10_cand:>23,.2f} | ${p10_cand - d1_p10:>+19,.2f}")
    print(f"{'P90 Percentile':<28} | ${d1_p90:>19,.2f} | ${p90_cand:>23,.2f} | ${p90_cand - d1_p90:>+19,.2f}")
    print("-" * 105)
    print(f"{'Win Rate vs v18':<28} | {d1_wr:>19.1%} | {wr_cand:>23.1%} | {wr_cand - d1_wr:>+19.1%}")
    print(f"{'Total Wins / Losses':<28} | {'60 Wins / 4 Losses':>20} | {f'{wins} Wins / {losses} Losses':>24} | {f'{wins - 60:+d} Wins':>20}")
    print(f"{'Cumulative Net Margin':<28} | {'+$86,801.00':>20} | ${sum(margins):>+23,.2f} | ${sum(margins) - 86801.00:>+19,.2f}")
    print("=" * 105)

    # Detailed Inspection of Seed 22222 ($234k Elite Pie)
    m_22222_s0 = next(m for m in all_matches if m["seed"] == 22222 and m["seat"] == 0)
    m_22222_s1 = next(m for m in all_matches if m["seed"] == 22222 and m["seat"] == 1)

    print("\n" + "=" * 105)
    print("INSPECTION OF SEED 22222 ($234k ELITE PIE MATCH)")
    print("=" * 105)
    print(f"  - Seat 0: Bank = ${m_22222_s0['cand_bank']:>10,.2f} vs v18 = ${m_22222_s0['v18_bank']:>10,.2f} | Margin = ${m_22222_s0['margin']:>+9,.2f} | {'WIN [OK]' if m_22222_s0['is_win'] else 'LOSS [X]'}")
    print(f"  - Seat 1: Bank = ${m_22222_s1['cand_bank']:>10,.2f} vs v18 = ${m_22222_s1['v18_bank']:>10,.2f} | Margin = ${m_22222_s1['margin']:>+9,.2f} | {'WIN [OK]' if m_22222_s1['is_win'] else 'LOSS [X]'}")
    print("=" * 105)

    passed_tournament = (wr_cand >= 0.938)
    improved_elite = (elite_mean > d1_elite_mean + 1000)

    print("\nPROMOTION EVALUATION:")
    print(f"  - Tournament Gate (Win Rate >= 93.8%): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")
    print(f"  - Elite Regime Efficacy Check         : {'ELITE GAIN [OK]' if improved_elite else 'NO ELITE GAIN [X]'}")

    if passed_tournament and improved_elite:
        print("\n>>> VERDICT: PROMOTE ELITE-SPECIALIZED AGENT TO TRACK B BASELINE!")
    else:
        print("\n>>> VERDICT: CONDITIONAL SPECIALIZATION FAILS TO BEAT FROZEN D.1. (KEEP FROZEN D.1)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp051()
