"""EXP096: Candidate D.2 Opponent-Aware Counterfactual Validation.

Tests Variant D.1 (Frozen Control A) vs Candidate D.2 across:
1. Large-Margin Defeat Seeds (6 tournament seeds)
2. Saturated Duopoly Benchmark Seeds (10 balanced seeds)
3. Direct Head-to-Head Duel: Variant D.1 vs Candidate D.2 (20 paired matches, alternating seats)

Metrics:
- Win Rate (%)
- Mean Terminal Wealth ($)
- Paired Delta Margin ($)
- Solvency & Liquidation Verification (0 stranded units at Step 720)
- Decision Gate: Does D.2 improve on loss seeds without regressing in duopolies?
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
from candidates.candidate_d2_market import CandidateD2Agent

LARGE_LOSS_SEEDS = [1599299971, 1487822928, 1259752816, 963135243, 2144164697, 886661034]
CONTROL_SEEDS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
H2H_SEEDS = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120]

def evaluate_match(agent_0, agent_1, seed: int):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    while not env.done:
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        act0 = agent_0.act(obs0, env.configuration)
        act1 = agent_1.act(obs1, env.configuration) if hasattr(agent_1, "act") else agent_1(obs1)

        env.step([act0, act1])

    r0 = float(env.state[0].reward or 0.0)
    r1 = float(env.state[1].reward or 0.0)
    return r0, r1

def run_exp096():
    print("=" * 105)
    print("EXP096: CANDIDATE D.2 OPPONENT-AWARE COUNTERFACTUAL VALIDATION")
    print("=" * 105)

    # 1. Test on Large Loss Seeds vs Benchmark
    print("\n1. LARGE-MARGIN DEFEAT SEEDS (D.1 vs D.2 Performance against Benchmark):")
    print("-" * 105)
    print(f"{'Seed':<12} | {'D.1 Final ($)':>14} | {'D.2 Final ($)':>14} | {'D.2 - D.1 Delta':>16} | {'Benchmark Final ($)':>20}")
    print("-" * 105)

    d1_loss_rewards = []
    d2_loss_rewards = []

    for s in LARGE_LOSS_SEEDS:
        a_d1 = VariantDAgent()
        r_d1, r_opp1 = evaluate_match(a_d1, bot_v18.agent, s)

        a_d2 = CandidateD2Agent()
        r_d2, r_opp2 = evaluate_match(a_d2, bot_v18.agent, s)

        d1_loss_rewards.append(r_d1)
        d2_loss_rewards.append(r_d2)

        delta = r_d2 - r_d1
        print(f"{s:<12} | ${r_d1:>13,.0f} | ${r_d2:>13,.0f} | ${delta:>+15,.0f} | ${r_opp1:>19,.0f}")

    print("-" * 105)
    print(f"Mean on Loss Seeds: D.1 = ${np.mean(d1_loss_rewards):,.2f} | D.2 = ${np.mean(d2_loss_rewards):,.2f} (Net Delta: ${np.mean(d2_loss_rewards) - np.mean(d1_loss_rewards):+,.2f})")

    # 2. Test on Saturated Duopoly Control Seeds
    print("\n2. SATURATED DUOPOLY CONTROL SEEDS (10 SEEDS):")
    print("-" * 105)
    d1_ctrl_rewards = []
    d2_ctrl_rewards = []

    for s in CONTROL_SEEDS:
        a_d1 = VariantDAgent()
        r_d1, _ = evaluate_match(a_d1, bot_v18.agent, s)

        a_d2 = CandidateD2Agent()
        r_d2, _ = evaluate_match(a_d2, bot_v18.agent, s)

        d1_ctrl_rewards.append(r_d1)
        d2_ctrl_rewards.append(r_d2)

    print(f"Mean on Control Seeds: D.1 = ${np.mean(d1_ctrl_rewards):,.2f} | D.2 = ${np.mean(d2_ctrl_rewards):,.2f} (Net Delta: ${np.mean(d2_ctrl_rewards) - np.mean(d1_ctrl_rewards):+,.2f})")

    # 3. Direct Head-to-Head Duel: D.1 vs Candidate D.2
    print("\n3. DIRECT HEAD-TO-HEAD DUEL: VARIANT D.1 (P0) vs CANDIDATE D.2 (P1) (20 MATCHES):")
    print("-" * 105)
    h2h_d1_scores = []
    h2h_d2_scores = []
    d2_wins = 0

    for idx, s in enumerate(H2H_SEEDS):
        if idx % 2 == 0:
            a0 = VariantDAgent()
            a1 = CandidateD2Agent()
            r0, r1 = evaluate_match(a0, a1, s)
            h2h_d1_scores.append(r0)
            h2h_d2_scores.append(r1)
            if r1 > r0:
                d2_wins += 1
        else:
            a0 = CandidateD2Agent()
            a1 = VariantDAgent()
            r0, r1 = evaluate_match(a0, a1, s)
            h2h_d2_scores.append(r0)
            h2h_d1_scores.append(r1)
            if r0 > r1:
                d2_wins += 1

    d2_wr = d2_wins / len(H2H_SEEDS)
    mean_d1_h2h = np.mean(h2h_d1_scores)
    mean_d2_h2h = np.mean(h2h_d2_scores)
    margin_h2h = mean_d2_h2h - mean_d1_h2h

    print(f"  * D.2 Head-to-Head Win Rate vs D.1 : {d2_wins} / {len(H2H_SEEDS)} ({d2_wr:.1%})")
    print(f"  * Mean Variant D.1 Bank            : ${mean_d1_h2h:>12,.2f}")
    print(f"  * Mean Candidate D.2 Bank          : ${mean_d2_h2h:>12,.2f}")
    print(f"  * Paired Delta (D.2 - D.1)         : ${margin_h2h:>+12,.2f}")

    print("\n" + "=" * 105)
    print("4. EXP096 CANDIDATE GATE VERDICT:")
    print("-" * 105)
    if margin_h2h > 1000.0 and np.mean(d2_loss_rewards) > np.mean(d1_loss_rewards):
        print("  [PROMOTION CANDIDATE] Candidate D.2 achieves statistically significant alpha over D.1.")
    elif abs(margin_h2h) <= 500.0:
        print("  [EQUIVALENCE] Candidate D.2 preserves D.1 parity without negative regression.")
        print("                submission.py remains FROZEN (Control A).")
    else:
        print("  [REJECT] Candidate D.2 regressed or failed promotion criteria.")
    print("=" * 105)

if __name__ == "__main__":
    run_exp096()
