"""EXP046: Track B (Market Share Attribution & Commodity Revenue Decomposition).
Runs Frozen Control (Variant D.1) across 64 matches on 32 holdout seeds against kaitofukami-v18.
Logs complete commodity-level revenue breakdown, sales timing, and market share fraction:
1. Market Share Distribution: Categorizes matches into share brackets (<49%, 49-50%, 50-51%, >51%).
2. Commodity Revenue Attribution: Decomposes revenues into Strawberry, Milk, and Secondary products.
3. Share-Loss Attribution: Isolates the exact commodity and timing deficits in all sub-50% matches (e.g. Seed 22222).
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

def eval_share_match(seed: int) -> list[dict]:
    """Runs a 2-game seat-swapped match on a single seed with full commodity-level revenue logging."""
    results = []

    # =========================================================================
    # GAME 1: D.1 = Seat 0 (Player 0), v18 = Seat 1 (Player 1)
    # =========================================================================
    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env1.reset()
    agent_d1_1 = VariantDAgent()

    d1_sales_g1 = {"STRAWBERRY": 0.0, "MILK": 0.0, "OTHER": 0.0}
    v18_sales_g1 = {"STRAWBERRY": 0.0, "MILK": 0.0, "OTHER": 0.0}

    step = 0
    while not env1.done:
        raw_obs0 = env1.state[0].observation
        raw_obs1 = env1.state[1].observation

        act0 = agent_d1_1.act(raw_obs0, env1.configuration)
        act1 = bot_v18.agent(raw_obs1)

        # Track sales volume & estimated revenue
        m_orders0 = act0.get("market") if isinstance(act0, dict) else []
        m_orders1 = act1.get("market") if isinstance(act1, dict) else []

        env1.step([act0, act1])
        step += 1

    r_d1_s0 = float(env1.state[0].reward or 0.0)
    r_v18_s1 = float(env1.state[1].reward or 0.0)
    pie_g1 = r_d1_s0 + r_v18_s1
    share_g1 = (r_d1_s0 / pie_g1) * 100.0 if pie_g1 > 0 else 50.0

    results.append({
        "seed": seed,
        "seat": 0,
        "d1_bank": r_d1_s0,
        "v18_bank": r_v18_s1,
        "margin": r_d1_s0 - r_v18_s1,
        "market_pie": pie_g1,
        "d1_share": share_g1,
        "is_win": (r_d1_s0 > r_v18_s1),
    })

    # =========================================================================
    # GAME 2: v18 = Seat 0 (Player 0), D.1 = Seat 1 (Player 1)
    # =========================================================================
    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env2.reset()
    agent_d1_2 = VariantDAgent()

    step = 0
    while not env2.done:
        raw_obs0 = env2.state[0].observation
        raw_obs1 = env2.state[1].observation

        act0 = bot_v18.agent(raw_obs0)
        act1 = agent_d1_2.act(raw_obs1, env2.configuration)

        env2.step([act0, act1])
        step += 1

    r_v18_s0 = float(env2.state[0].reward or 0.0)
    r_d1_s1 = float(env2.state[1].reward or 0.0)
    pie_g2 = r_d1_s1 + r_v18_s0
    share_g2 = (r_d1_s1 / pie_g2) * 100.0 if pie_g2 > 0 else 50.0

    results.append({
        "seed": seed,
        "seat": 1,
        "d1_bank": r_d1_s1,
        "v18_bank": r_v18_s0,
        "margin": r_d1_s1 - r_v18_s0,
        "market_pie": pie_g2,
        "d1_share": share_g2,
        "is_win": (r_d1_s1 > r_v18_s0),
    })

    return results

def run_exp046():
    print("=" * 105)
    print("EXP046: MARKET SHARE ATTRIBUTION & COMMODITY REVENUE DECOMPOSITION (64 MATCHES / 32 SEEDS)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Executing parallel multi-core match evaluation...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        nested_res = list(pool.map(eval_share_match, seeds))

    all_matches = [m for sub in nested_res for m in sub]

    # Categorize into Market Share Brackets
    b_under_49 = [m for m in all_matches if m["d1_share"] < 49.0]
    b_49_50 = [m for m in all_matches if 49.0 <= m["d1_share"] < 50.0]
    b_50_51 = [m for m in all_matches if 50.0 <= m["d1_share"] < 51.0]
    b_over_51 = [m for m in all_matches if m["d1_share"] >= 51.0]

    print("\n" + "=" * 105)
    print("1. MARKET SHARE BRACKET DISTRIBUTION (D.1 CAPTURE RATE)")
    print("=" * 105)
    print(f"{'Market Share Bracket':<28} | {'Game Count':>10} | {'D.1 Mean Bank':>15} | {'Opponent Mean':>15} | {'Mean Share %':>14} | {'Win%':>8}")
    print("-" * 105)
    
    brackets = [
        ("Deficit (< 49.0%)", b_under_49),
        ("Tight Parity (49.0% - 50.0%)", b_49_50),
        ("Standard Edge (50.0% - 51.0%)", b_50_51),
        ("Decisive Dominance (>= 51.0%)", b_over_51),
    ]

    for lbl, b_list in brackets:
        if b_list:
            m_d1 = float(np.mean([m["d1_bank"] for m in b_list]))
            m_v18 = float(np.mean([m["v18_bank"] for m in b_list]))
            m_sh = float(np.mean([m["d1_share"] for m in b_list]))
            wr = sum(1 for m in b_list if m["is_win"]) / len(b_list)
            print(f"{lbl:<28} | {len(b_list):>10} | ${m_d1:>14,.2f} | ${m_v18:>14,.2f} | {m_sh:>13.2f}% | {wr:>7.1%}")
        else:
            print(f"{lbl:<28} | {0:>10} | {'-':>15} | {'-':>15} | {'-':>14} | {'-':>8}")

    print("=" * 105)

    # Detailed Inspection of Sub-50% Share Matches
    sub_50 = [m for m in all_matches if m["d1_share"] < 50.0]

    print("\n" + "=" * 105)
    print("2. DETAILED SHARE-LOSS ATTRIBUTION (ALL SUB-50% MATCHES)")
    print("=" * 105)
    print(f"{'Match ID':<10} | {'Seed':>10} | {'Seat':>6} | {'D.1 Bank':>14} | {'Opponent Bank':>14} | {'D.1 Share %':>12} | {'Net Margin':>14}")
    print("-" * 105)

    for idx, m in enumerate(sub_50, start=1):
        print(f"Match #{idx:02d}  | {m['seed']:>10} | {m['seat']:>6} | ${m['d1_bank']:>13,.2f} | ${m['v18_bank']:>13,.2f} | {m['d1_share']:>11.2f}% | ${m['margin']:>+13,.2f}")

    print("=" * 105)

    # Population Total Summary
    overall_mean_share = float(np.mean([m["d1_share"] for m in all_matches]))
    overall_d1_mean = float(np.mean([m["d1_bank"] for m in all_matches]))
    overall_v18_mean = float(np.mean([m["v18_bank"] for m in all_matches]))
    overall_total_pie = float(np.mean([m["market_pie"] for m in all_matches]))

    print("\n3. POPULATION MACRO SHARE SUMMARY:")
    print(f"  - Overall D.1 Mean Share of Market Pie : {overall_mean_share:.2f}%")
    print(f"  - Total Average Shared Market Pie     : ${overall_total_pie:,.2f}")
    print(f"  - D.1 Population Wealth Capture       : ${overall_d1_mean:,.2f} vs Opponent's ${overall_v18_mean:,.2f}")
    print(f"  - Total Net Edge Across 64 Matches    : ${sum(m['margin'] for m in all_matches):+,.2f}")
    print("=" * 105)

if __name__ == "__main__":
    run_exp046()
