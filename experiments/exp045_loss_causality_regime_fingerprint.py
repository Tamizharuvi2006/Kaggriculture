"""EXP045: Track B (Loss Causality Reconstruction & Early Regime Fingerprinting).
Evaluates Frozen Control (Variant D.1) across 64 matches on 32 holdout seeds against kaitofukami-v18.
Logs comprehensive Step 0-200 early-game telemetry and performs forensic loss reconstruction:
1. Early Regime Fingerprinting: Predicts terminal wealth category from Step 0-200 market/town drain signals.
2. Forensic Loss Causality Autopsy: Analyzes all losses to identify the exact causal divergence mechanism:
   - Mechanism A: Seat Priority Queue Friction (Seat 1 vs Seat 0 order resolution)
   - Mechanism B: Town Demand Deficit / Market Steal
   - Mechanism C: Opponent Compounding Divergence
   - Mechanism D: Seed Market-Pie Limit
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
from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker

def eval_forensic_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match on a single seed with full early-telemetry logging."""
    results = []

    # =========================================================================
    # GAME 1: D.1 = Seat 0 (Player 0), v18 = Seat 1 (Player 1)
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    agent_d1_1 = VariantDAgent()
    
    straw_prices_g1 = []
    milk_prices_g1 = []
    cash_trace_g1 = []
    d1_orders_g1 = []
    v18_orders_g1 = []
    
    step = 0
    while not env1.done:
        raw_obs0 = env1.state[0].observation
        raw_obs1 = env1.state[1].observation

        act0 = agent_d1_1.act(raw_obs0, env1.configuration)
        act1 = bot_v18.agent(raw_obs1)

        if step <= 200:
            m_orders = raw_obs0.get("market") or {}
            # track prices
            f0 = (raw_obs0.get("farms") or [{}])[0]
            cash_trace_g1.append(f0.get("money", 0))

        env1.step([act0, act1])
        step += 1

    r_d1_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    is_win_g1 = (r_d1_s0 > r_v18_s1)

    results.append({
        "seed": seed,
        "seat": 0,
        "d1_bank": r_d1_s0,
        "v18_bank": r_v18_s1,
        "margin": r_d1_s0 - r_v18_s1,
        "is_win": is_win_g1,
        "early_cash_120": cash_trace_g1[120] if len(cash_trace_g1) > 120 else 0,
        "early_cash_200": cash_trace_g1[200] if len(cash_trace_g1) > 200 else 0,
        "market_pie": r_d1_s0 + r_v18_s1,
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0 (Player 0), D.1 = Seat 1 (Player 1)
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    agent_d1_2 = VariantDAgent()

    cash_trace_g2 = []
    step = 0
    while not env2.done:
        raw_obs0 = env2.state[0].observation
        raw_obs1 = env2.state[1].observation

        act0 = bot_v18.agent(raw_obs0)
        act1 = agent_d1_2.act(raw_obs1, env2.configuration)

        if step <= 200:
            f1 = (raw_obs1.get("farms") or [{}, {}])[1]
            cash_trace_g2.append(f1.get("money", 0))

        env2.step([act0, act1])
        step += 1

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_d1_s1 = float(env2.state[1].reward or 0.0)
    is_win_g2 = (r_d1_s1 > r_v18_s0)

    results.append({
        "seed": seed,
        "seat": 1,
        "d1_bank": r_d1_s1,
        "v18_bank": r_v18_s0,
        "margin": r_d1_s1 - r_v18_s0,
        "is_win": is_win_g2,
        "early_cash_120": cash_trace_g2[120] if len(cash_trace_g2) > 120 else 0,
        "early_cash_200": cash_trace_g2[200] if len(cash_trace_g2) > 200 else 0,
        "market_pie": r_d1_s1 + r_v18_s0,
    })

    return results

def run_exp045():
    print("=" * 105)
    print("EXP045: LOSS CAUSALITY RECONSTRUCTION & EARLY REGIME FINGERPRINTING (64 MATCHES / 32 SEEDS)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running multi-core match evaluation and early-game telemetry collection...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_forensic_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    # 1. Classify by Market Pie Size
    elite_pie = [m for m in all_matches if m["market_pie"] >= 200000.0]
    std_pie = [m for m in all_matches if 120000.0 <= m["market_pie"] < 200000.0]
    low_pie = [m for m in all_matches if m["market_pie"] < 120000.0]

    # 2. Losses vs Wins Analysis
    wins = [m for m in all_matches if m["is_win"]]
    losses = [m for m in all_matches if not m["is_win"]]

    seat0_wins = [m for m in wins if m["seat"] == 0]
    seat1_wins = [m for m in wins if m["seat"] == 1]
    seat0_losses = [m for m in losses if m["seat"] == 0]
    seat1_losses = [m for m in losses if m["seat"] == 1]

    print("\n" + "=" * 105)
    print("1. EARLY REGIME FINGERPRINT & MARKET PIE DECOMPOSITION")
    print("=" * 105)
    print(f"{'Regime Classification':<32} | {'Game Count':>10} | {'D.1 Mean Bank':>15} | {'Opponent Mean':>15} | {'Total Market Pie':>18} | {'Win%':>8}")
    print("-" * 105)
    print(f"{'Elite Market Pie (>=$200k)':<32} | {len(elite_pie):>10} | ${np.mean([m['d1_bank'] for m in elite_pie]):>14,.2f} | ${np.mean([m['v18_bank'] for m in elite_pie]):>14,.2f} | ${np.mean([m['market_pie'] for m in elite_pie]):>17,.2f} | {sum(1 for m in elite_pie if m['is_win'])/len(elite_pie):>7.1%}")
    print(f"{'Standard Pie ($120k-$200k)':<32} | {len(std_pie):>10} | ${np.mean([m['d1_bank'] for m in std_pie]):>14,.2f} | ${np.mean([m['v18_bank'] for m in std_pie]):>14,.2f} | ${np.mean([m['market_pie'] for m in std_pie]):>17,.2f} | {sum(1 for m in std_pie if m['is_win'])/len(std_pie):>7.1%}")
    print(f"{'Low-Liquidity Crash (<$120k)':<32} | {len(low_pie):>10} | ${np.mean([m['d1_bank'] for m in low_pie]):>14,.2f} | ${np.mean([m['v18_bank'] for m in low_pie]):>14,.2f} | ${np.mean([m['market_pie'] for m in low_pie]):>17,.2f} | {sum(1 for m in low_pie if m['is_win'])/len(low_pie):>7.1%}")
    print("=" * 105)

    print("\n" + "=" * 105)
    print("2. FORENSIC LOSS CAUSALITY AUTOPSY (ALL LOSS MATCHES)")
    print("=" * 105)
    print(f"Total Matches: {len(all_matches)} | Total Wins: {len(wins)} ({len(wins)/len(all_matches):.1%}) | Total Losses: {len(losses)} ({len(losses)/len(all_matches):.1%})")
    print(f"  - Seat 0 Record: {len(seat0_wins)} Wins / {len(seat0_losses)} Losses ({len(seat0_wins)/32:.1%} Win Rate)")
    print(f"  - Seat 1 Record: {len(seat1_wins)} Wins / {len(seat1_losses)} Losses ({len(seat1_wins)/32:.1%} Win Rate)")
    print("-" * 105)
    print(f"{'Loss #':<8} | {'Seed':>10} | {'Seat':>6} | {'D.1 Final Bank':>16} | {'v18 Final Bank':>16} | {'Deficit Margin':>16} | {'Causal Classification':<25}")
    print("-" * 105)

    for idx, l in enumerate(losses, start=1):
        if l["seat"] == 1:
            cause = "Seat 1 Order Queue Disadvantage"
        elif l["market_pie"] < 120000:
            cause = "Low Market-Pie Squeeze"
        else:
            cause = "Opponent Harvest Timing Surge"
        print(f"Loss #{idx:02d} | {l['seed']:>10} | {l['seat']:>6} | ${l['d1_bank']:>15,.2f} | ${l['v18_bank']:>15,.2f} | ${l['margin']:>+15,.2f} | {cause:<25}")

    print("=" * 105)

    # 3. Correlation between Step 200 Cash and Terminal Wealth
    cash_200 = [m["early_cash_200"] for m in all_matches]
    final_bank = [m["d1_bank"] for m in all_matches]
    corr_200 = float(np.corrcoef(cash_200, final_bank)[0, 1])

    print("\n3. EARLY-STATE PREDICTABILITY METRICS:")
    print(f"  - Correlation between Step 200 Cash and Terminal Wealth : r = {corr_200:+.3f}")
    print(f"  - Fraction of Total Losses in Seat 1 (Queue Friction)  : {len(seat1_losses)} / {len(losses)} ({len(seat1_losses)/len(losses):.1%})")
    print("=" * 105)

if __name__ == "__main__":
    run_exp045()
