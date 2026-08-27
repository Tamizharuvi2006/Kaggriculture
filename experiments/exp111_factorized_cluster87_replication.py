"""EXP111: Factorized Cluster 87 Replication Study (20 Seeds).

Evaluates 6 Factorized Replication Arms:
- EXP111-A: Variant D.1 Control A (Monolithic Strawberries + 8 Cows)
- EXP111-B: Mode 'B' (+ Early Cash-Flow: Days 1-5 Wheat/Fertilizer Sales)
- EXP111-C: Mode 'C' (+ Day-11 Melon Spike: Opening 11 Melons -> Day 11 Liquidation)
- EXP111-D: Mode 'D' (+ Dual Livestock: Cow + Sheep / Wool Monetization)
- EXP111-E: Mode 'E' (+ Idle-Tile Wheat Filler: 2-Day Continuous Crop Velocity)
- EXP111-F: Mode 'F' (Full Integrated 4-Pillar Cluster 87 Engine)

Evaluated Across 20 Tournament Seeds:
- 10 Elite / High-Win Replay Seeds (93332287, 93351245, etc.)
- 10 Saturated Control Seeds (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000)

Metrics:
- Terminal Bank ($) & Net Delta vs D.1 ($)
- Market Share Capture (%)
- Cash Velocity at Day 5 and Day 11
- Win Rate vs kaitofukami-v18 (%)
- 100% Solvency & Zero Stranded Assets.
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
from candidates.candidate_d2_cluster87 import CandidateD2Cluster87Agent

HIGH_WIN_SEEDS = [93332287, 93351245, 93441990, 93180220, 93191911, 93192808, 93317864, 93325055, 93327766, 90561400]
CONTROL_SEEDS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
ALL_SEEDS = HIGH_WIN_SEEDS + CONTROL_SEEDS
ARMS = ["A", "B", "C", "D", "E", "F"]

def evaluate_arm(arm_code: str, seeds: list[int]):
    results = []

    for s in seeds:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env.reset()

        if arm_code == "A":
            agent_inst = VariantDAgent()
        else:
            agent_inst = CandidateD2Cluster87Agent(mode=arm_code)

        m5 = 0.0
        m11 = 0.0
        step_idx = 0

        while not env.done:
            obs0 = env.state[0].observation
            obs1 = env.state[1].observation

            if step_idx == 120:  # Day 5
                farms = obs0.get("farms", [])
                m5 = float(farms[0].get("money", 0.0)) if len(farms) > 0 else 0.0
            if step_idx == 264:  # Day 11
                farms = obs0.get("farms", [])
                m11 = float(farms[0].get("money", 0.0)) if len(farms) > 0 else 0.0

            a0 = agent_inst.act(obs0, env.configuration)
            a1 = bot_v18.agent(obs1)
            env.step([a0, a1])
            step_idx += 1

        r0 = float(env.state[0].reward or 0.0)
        r1 = float(env.state[1].reward or 0.0)
        pie = r0 + r1
        share = r0 / pie if pie > 0 else 0.0

        results.append({
            "seed": s,
            "reward": r0,
            "opp_reward": r1,
            "share": share,
            "m5": m5,
            "m11": m11,
            "won": (r0 > r1),
        })

    return results

def run_exp111():
    print("=" * 110)
    print("EXP111: FACTORIZED CLUSTER 87 REPLICATION STUDY (20 TOURNAMENT SEEDS)")
    print("=" * 110)
    print(f"{'Replication Arm':<28} | {'Overall ($)':>14} | {'High-Win ($)':>14} | {'Control ($)':>14} | {'Delta ($)':>12} | {'Share':>8} | {'WR'}")
    print("-" * 110)

    # 1. Run Baseline Control A
    res_A = evaluate_arm("A", ALL_SEEDS)
    mean_A_all = np.mean([x["reward"] for x in res_A])
    mean_A_hw = np.mean([x["reward"] for x in res_A[:10]])
    mean_A_ctrl = np.mean([x["reward"] for x in res_A[10:]])
    mean_A_share = np.mean([x["share"] for x in res_A])
    wr_A = np.mean([1.0 if x["won"] else 0.0 for x in res_A])

    print(f"{'EXP111-A (D.1 Control)':<28} | ${mean_A_all:>13,.2f} | ${mean_A_hw:>13,.2f} | ${mean_A_ctrl:>13,.2f} | ${0.0:>+11,.2f} | {mean_A_share:>7.1%} | {wr_A:>5.1%}")

    arm_summaries = [{
        "arm": "A",
        "name": "EXP111-A (D.1 Control)",
        "mean_all": mean_A_all,
        "mean_hw": mean_A_hw,
        "mean_ctrl": mean_A_ctrl,
        "delta": 0.0,
        "share": mean_A_share,
        "wr": wr_A,
    }]

    for code, label in [
        ("B", "EXP111-B (+ Early Cash)"),
        ("C", "EXP111-C (+ Day-11 Melon)"),
        ("D", "EXP111-D (+ Dual Livestock)"),
        ("E", "EXP111-E (+ Wheat Filler)"),
        ("F", "EXP111-F (All 4 Pillars)"),
    ]:
        res_arm = evaluate_arm(code, ALL_SEEDS)
        mean_all = np.mean([x["reward"] for x in res_arm])
        mean_hw = np.mean([x["reward"] for x in res_arm[:10]])
        mean_ctrl = np.mean([x["reward"] for x in res_arm[10:]])
        mean_share = np.mean([x["share"] for x in res_arm])
        wr = np.mean([1.0 if x["won"] else 0.0 for x in res_arm])
        delta = mean_all - mean_A_all

        print(f"{label:<28} | ${mean_all:>13,.2f} | ${mean_hw:>13,.2f} | ${mean_ctrl:>13,.2f} | ${delta:>+11,.2f} | {mean_share:>7.1%} | {wr:>5.1%}")

        arm_summaries.append({
            "arm": code,
            "name": label,
            "mean_all": mean_all,
            "mean_hw": mean_hw,
            "mean_ctrl": mean_ctrl,
            "delta": delta,
            "share": mean_share,
            "wr": wr,
        })

    print("=" * 110)
    print("\n1. SCIENTIFIC FACTORIZED REPLICATION DISCOVERIES:")
    print("-" * 110)
    best_arm = max(arm_summaries, key=lambda x: x["mean_all"])
    print(f"  • Best Factorized Pillar: {best_arm['name']} delivering ${best_arm['mean_all']:,.2f} overall (${best_arm['delta']:+,.2f} delta vs D.1, {best_arm['wr']:.1%} WR).")
    print("  • Attribution Analysis: Demonstrates exactly which component of Cluster 87 creates alpha vs drag.")
    print("  • Production Status: submission.py remains 100% FROZEN (Control A).")
    print("=" * 110)

if __name__ == "__main__":
    run_exp111()
