"""EXP036: Track B (Candidate EXP036 - Opponent Dependency & Asymmetric Market Pressure Tournament).
Evaluates Opponent Warfare on top of the APEX physical substrate
against Frozen Control (Variant D.1) and kaitofukami-v18 across 64 matches on 32 holdout seeds.
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
from engine.macro_money.exp036_warfare_agent import OpponentWarfareAgent

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

def run_exp036():
    print("=" * 95)
    print("EXP036: TRACK B CANDIDATE EXP036 (OPPONENT WARFARE) vs CONTROL D.1 (64 MATCHES / 32 SEEDS)")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    warfare_banks = []
    v18_banks = []
    warfare_wins = 0.0

    print(f"Simulating Candidate EXP036 vs kaitofukami-v18 across {len(seeds)} seeds (64 matches)...")
    for s in seeds:
        # Match 1: Warfare = Seat 0, v18 = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        w1 = OpponentWarfareAgent()
        while not env1.done:
            env1.step([w1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        r_w_s0 = float(env1.state[0].reward or 0.0)
        r_v_s1 = float(env1.state[1].reward or 0.0)
        if r_w_s0 > r_v_s1: warfare_wins += 1.0
        elif r_w_s0 == r_v_s1: warfare_wins += 0.5

        # Match 2: v18 = Seat 0, Warfare = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        w2 = OpponentWarfareAgent()
        while not env2.done:
            env2.step([bot_v18.agent(env2.state[0].observation), w2.act(env2.state[1].observation)])
        r_v_s0 = float(env2.state[0].reward or 0.0)
        r_w_s1 = float(env2.state[1].reward or 0.0)
        if r_w_s1 > r_v_s0: warfare_wins += 1.0
        elif r_w_s1 == r_v_s0: warfare_wins += 0.5

        warfare_banks.extend([r_w_s0, r_w_s1])
        v18_banks.extend([r_v_s1, r_v_s0])

    stats_w = compute_distribution_stats(warfare_banks)
    stats_opp = compute_distribution_stats(v18_banks)
    win_rate_w = warfare_wins / (len(seeds) * 2)

    # Load Frozen D.1 baseline stats
    with open(os.path.join(BASE_DIR, "reports", "D1_FINAL_COIN_DISTRIBUTION.json"), "r") as f:
        d1_data = json.load(f)
    stats_d1 = d1_data["overall_cand"]

    print("\n" + "=" * 95)
    print("EXP036 CANDIDATE WARFARE COMPARATIVE REPORT (64 MATCHES / 32 SEEDS)")
    print("=" * 95)
    print(f"{'Metric':<22} | {'Frozen Control (D.1)':>20} | {'Candidate EXP036 (Warfare)':>27} | {'Delta (Warfare - D.1)':>22}")
    print("-" * 95)
    print(f"{'Mean / Average Bank':<22} | ${stats_d1['mean']:>19,.2f} | ${stats_w['mean']:>26,.2f} | ${stats_w['mean'] - stats_d1['mean']:>+21,.2f}")
    print(f"{'Median Bank':<22} | ${stats_d1['median']:>19,.2f} | ${stats_w['median']:>26,.2f} | ${stats_w['median'] - stats_d1['median']:>+21,.2f}")
    print(f"{'Minimum Bank (Floor)':<22} | ${stats_d1['min']:>19,.2f} | ${stats_w['min']:>26,.2f} | ${stats_w['min'] - stats_d1['min']:>+21,.2f}")
    print(f"{'Maximum Bank (Peak)':<22} | ${stats_d1['max']:>19,.2f} | ${stats_w['max']:>26,.2f} | ${stats_w['max'] - stats_d1['max']:>+21,.2f}")
    print(f"{'Standard Deviation':<22} | ${stats_d1['std']:>19,.2f} | ${stats_w['std']:>26,.2f} | ${stats_w['std'] - stats_d1['std']:>+21,.2f}")
    print("-" * 95)
    print(f"{'P10 Percentile':<22} | ${stats_d1['p10']:>19,.2f} | ${stats_w['p10']:>26,.2f} | ${stats_w['p10'] - stats_d1['p10']:>+21,.2f}")
    print(f"{'P25 Percentile':<22} | ${stats_d1['p25']:>19,.2f} | ${stats_w['p25']:>26,.2f} | ${stats_w['p25'] - stats_d1['p25']:>+21,.2f}")
    print(f"{'P75 Percentile':<22} | ${stats_d1['p75']:>19,.2f} | ${stats_w['p75']:>26,.2f} | ${stats_w['p75'] - stats_d1['p75']:>+21,.2f}")
    print(f"{'P90 Percentile':<22} | ${stats_d1['p90']:>19,.2f} | ${stats_w['p90']:>26,.2f} | ${stats_w['p90'] - stats_d1['p90']:>+21,.2f}")
    print("-" * 95)
    print(f"{'Win Rate vs v18':<22} | {'90.6%':>20} | {win_rate_w:>26.1%} | {win_rate_w - 0.906:>+21.1%}")
    print(f"{'Opponent Mean Wealth':<22} | {'$77,298.08':>20} | ${stats_opp['mean']:>26,.2f} | ${stats_opp['mean'] - 77298.08:>+21,.2f}")
    print("=" * 95)

    passed_money = (stats_w['mean'] > stats_d1['mean'])
    passed_tournament = (win_rate_w >= 0.85)

    print("\nPROMOTION GATE EVALUATION:")
    print(f"  - Money Gate (Mean > ${stats_d1['mean']:,.2f})     : {'PASSED [OK]' if passed_money else 'FAILED [X]'}")
    print(f"  - Tournament Gate (Win Rate >= 85.0% vs v18): {'PASSED [OK]' if passed_tournament else 'FAILED [X]'}")

    if passed_money and passed_tournament:
        print("\n>>> VERDICT: PROMOTE CANDIDATE EXP036 AS TRACK B BASELINE!")
    else:
        print("\n>>> VERDICT: CANDIDATE EXP036 DOES NOT EXCEED CONTROL D.1. (KEEP FROZEN D.1)")
    print("=" * 95)

if __name__ == "__main__":
    run_exp036()
