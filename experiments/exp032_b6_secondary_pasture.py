"""EXP032: Track B (Candidate B6 - Secondary Pasture Evaluation).
Tests:
- B6.0 (Control D.1): 8 Animals (1 Pasture)
- B6.1: 10 Animals (2 Pastures)
- B6.2: 12 Animals (2 Pastures)
- B6.3: 14 Animals (2 Pastures)
- B6.4: 16 Animals (2 Pastures)
Across holdout seeds against kaitofukami-v18.
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
from engine.macro_money.b6_secondary_pasture_agent import B6SecondaryPastureAgent

def run_exp032():
    print("=" * 105)
    print("EXP032: TRACK B CANDIDATE B6 (SECONDARY PASTURE ARCHITECTURE EVALUATION)")
    print("=" * 105)

    seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 22222]

    configs = [
        ("B6.0: Control D.1 (8 Animals)", 8),
        ("B6.1: 10 Animals (2 Pastures)", 10),
        ("B6.2: 12 Animals (2 Pastures)", 12),
        ("B6.3: 14 Animals (2 Pastures)", 14),
        ("B6.4: 16 Animals (2 Pastures)", 16),
    ]

    results = []

    for name, target_anim in configs:
        cand_banks = []
        wins = 0.0
        for s in seeds:
            # Match 1: Cand = Seat 0, v18 = Seat 1
            env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env1.reset()
            a1 = B6SecondaryPastureAgent(target_animals=target_anim)
            while not env1.done:
                env1.step([a1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
            r_c_s0 = float(env1.state[0].reward or 0.0)
            r_v_s1 = float(env1.state[1].reward or 0.0)
            if r_c_s0 > r_v_s1: wins += 1.0
            elif r_c_s0 == r_v_s1: wins += 0.5

            # Match 2: v18 = Seat 0, Cand = Seat 1
            env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env2.reset()
            a2 = B6SecondaryPastureAgent(target_animals=target_anim)
            while not env2.done:
                env2.step([bot_v18.agent(env2.state[0].observation), a2.act(env2.state[1].observation)])
            r_v_s0 = float(env2.state[0].reward or 0.0)
            r_c_s1 = float(env2.state[1].reward or 0.0)
            if r_c_s1 > r_v_s0: wins += 1.0
            elif r_c_s1 == r_v_s0: wins += 0.5

            cand_banks.extend([r_c_s0, r_c_s1])

        arr = np.array(cand_banks)
        mean_b = float(np.mean(arr))
        med_b = float(np.median(arr))
        max_b = float(np.max(arr))
        min_b = float(np.min(arr))
        p10_b = float(np.percentile(arr, 10))
        p90_b = float(np.percentile(arr, 90))
        win_r = wins / (len(seeds) * 2)

        results.append({
            "name": name,
            "target": target_anim,
            "mean": mean_b, "median": med_b,
            "max": max_b, "min": min_b,
            "p10": p10_b, "p90": p90_b,
            "win_rate": win_r,
        })
        print(f"  [DONE] {name:<35} -> Mean: ${mean_b:>10,.2f} | Peak: ${max_b:>10,.2f} | Win%: {win_r:>6.1%}")

    print("\n" + "=" * 105)
    print("EXP032 SECONDARY PASTURE RESULTS (16 Matches per Configuration on 8 Holdout Seeds)")
    print("=" * 105)
    print(f"{'Configuration':<32} | {'Mean Bank':>12} | {'Median':>12} | {'Floor (Min)':>12} | {'Peak (Max)':>12} | {'P90':>12} | {'Win%':>6}")
    print("-" * 105)

    for r in results:
        print(f"{r['name']:<32} | ${r['mean']:>11,.2f} | ${r['median']:>11,.2f} | ${r['min']:>11,.2f} | ${r['max']:>11,.2f} | ${r['p90']:>11,.2f} | {r['win_rate']:>5.1%}")

    best_mean = max(results, key=lambda x: x["mean"])
    print("\n" + "=" * 105)
    print(f"TOP SECONDARY PASTURE CONFIGURATION: {best_mean['name']} -> Mean: ${best_mean['mean']:,.2f} | Peak: ${best_mean['max']:,.2f} | Win%: {best_mean['win_rate']:.1%}")
    print("=" * 105)

if __name__ == "__main__":
    run_exp032()
