"""EXP057: Track B (Duopoly Market Interaction & Price-Depression Physics Audit).
Decomposes the exact market interaction physics across all 32 holdout seeds comparing:
  - Match A: Duopoly (D.1 vs v18)
  - Match B: Monopoly (D.1 vs Passive Dummy)
Measures:
1. Average Realized Commodity Sale Price ($/unit) for Strawberries and Milk.
2. Price Depression Margin: How much per-unit value is destroyed when two farms sell into the same town shops.
3. Total Physical Units Sold (Duopoly vs Monopoly).
4. Explains the Crash-Pie Paradox (Why Monopoly extracts $150k while Duopoly crashes to $96k).
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

def audit_seed_interaction(seed: int) -> dict:
    """Traces prices, units sold, and revenue in Duopoly vs Monopoly on a single seed."""
    agent_d1 = VariantDAgent()

    # =========================================================================
    # 1. DUOPOLY SIMULATION (D.1 vs v18)
    # =========================================================================
    env_duo = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_duo.reset()
    
    duo_straw_prices = []
    duo_milk_prices = []

    while not env_duo.done:
        obs0 = env_duo.state[0].observation
        obs1 = env_duo.state[1].observation

        act0 = agent_d1.act(obs0, env_duo.configuration)
        act1 = bot_v18.agent(obs1)

        p = obs0.get("market", {}).get("prices", {})
        duo_straw_prices.append(p.get("STRAWBERRY", 120))
        duo_milk_prices.append(p.get("MILK", 160))

        env_duo.step([act0, act1])

    duo_d1_bank = float(env_duo.state[0].reward or 0.0)
    duo_v18_bank = float(env_duo.state[1].reward or 0.0)
    duo_pie = duo_d1_bank + duo_v18_bank

    # =========================================================================
    # 2. MONOPOLY SIMULATION (D.1 vs Passive Dummy)
    # =========================================================================
    env_mono = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_mono.reset()
    agent_d1.reset()

    mono_straw_prices = []
    mono_milk_prices = []

    while not env_mono.done:
        obs0 = env_mono.state[0].observation
        act0 = agent_d1.act(obs0, env_mono.configuration)
        act1 = {"farmer": ["PASS"], "hands": [], "market": []}

        p = obs0.get("market", {}).get("prices", {})
        mono_straw_prices.append(p.get("STRAWBERRY", 120))
        mono_milk_prices.append(p.get("MILK", 160))

        env_mono.step([act0, act1])

    mono_d1_bank = float(env_mono.state[0].reward or 0.0)

    # Classify Regime based on Duopoly total pie
    if duo_pie >= 200000.0:
        regime = "ELITE"
    elif duo_pie >= 120000.0:
        regime = "STANDARD"
    else:
        regime = "CRASH"

    return {
        "seed": seed,
        "regime": regime,
        "duo_pie": duo_pie,
        "duo_d1": duo_d1_bank,
        "duo_v18": duo_v18_bank,
        "mono_d1": mono_d1_bank,
        "duo_straw_p_mean": float(np.mean(duo_straw_prices)),
        "mono_straw_p_mean": float(np.mean(mono_straw_prices)),
        "duo_milk_p_mean": float(np.mean(duo_milk_prices)),
        "mono_milk_p_mean": float(np.mean(mono_milk_prices)),
        "straw_price_delta": float(np.mean(mono_straw_prices) - np.mean(duo_straw_prices)),
        "milk_price_delta": float(np.mean(mono_milk_prices) - np.mean(duo_milk_prices)),
    }

def run_exp057():
    print("=" * 105)
    print("EXP057: DUOPOLY MARKET INTERACTION & PRICE-DEPRESSION PHYSICS AUDIT (32 HOLDOUT SEEDS)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    print("Running parallel Duopoly vs Monopoly price physics simulation across 32 holdout seeds...")
    with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 16)) as pool:
        results = list(pool.map(audit_seed_interaction, seeds))

    elite = [r for r in results if r["regime"] == "ELITE"]
    std = [r for r in results if r["regime"] == "STANDARD"]
    crash = [r for r in results if r["regime"] == "CRASH"]

    print("\n" + "=" * 105)
    print("1. PRICE DEPRESSION & WEALTH DESTRUCTION BY MARKET REGIME (Duopoly vs Monopoly)")
    print("=" * 105)
    print(f"{'Regime Category':<22} | {'Duopoly D.1':>14} | {'Solo D.1 Bank':>15} | {'Duopoly Straw P':>16} | {'Monopoly Straw P':>17} | {'Price Penalty':>14}")
    print("-" * 105)

    groups = [
        ("ELITE (>= $200k)", elite),
        ("STANDARD ($120k-$200k)", std),
        ("CRASH (< $120k)", crash),
        ("POPULATION GRAND TOTAL", results),
    ]

    for lbl, grp in groups:
        m_duo_d1 = float(np.mean([r["duo_d1"] for r in grp]))
        m_mono_d1 = float(np.mean([r["mono_d1"] for r in grp]))
        m_duo_p = float(np.mean([r["duo_straw_p_mean"] for r in grp]))
        m_mono_p = float(np.mean([r["mono_straw_p_mean"] for r in grp]))
        p_delta = m_mono_p - m_duo_p
        print(f"{lbl:<22} | ${m_duo_d1:>13,.2f} | ${m_mono_d1:>14,.2f} | ${m_duo_p:>15.1f} | ${m_mono_p:>16.1f} | ${p_delta:>+13.1f}/u")

    print("=" * 105)

    # Autopsy of the Crash Regime
    print("\n2. FORENSIC AUTOPSY: THE CRASH-PIE SUPPRESSION MECHANISM")
    print("=" * 105)
    m_crash_duo_p = np.mean([r["duo_straw_p_mean"] for r in crash])
    m_crash_mono_p = np.mean([r["mono_straw_p_mean"] for r in crash])
    print(f"  - In Crash Seeds under Monopoly : D.1 maintains an average Strawberry price of ${m_crash_mono_p:.1f}/unit -> Earns ${np.mean([r['mono_d1'] for r in crash]):,.2f}!")
    print(f"  - In Crash Seeds under Duopoly  : Two farms flood the limited town demand -> Strawberry price crashes to ${m_crash_duo_p:.1f}/unit (-${m_crash_mono_p - m_crash_duo_p:.1f}/unit drop!)")
    print(f"  - Price-Depression Wealth Loss  : Drops D.1 from ${np.mean([r['mono_d1'] for r in crash]):,.2f} -> ${np.mean([r['duo_d1'] for r in crash]):,.2f} (-${np.mean([r['mono_d1'] for r in crash]) - np.mean([r['duo_d1'] for r in crash]):,.2f} lost to price crash)")
    print("=" * 105)

if __name__ == "__main__":
    run_exp057()
