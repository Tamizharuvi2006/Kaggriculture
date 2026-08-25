"""EXP038: Track B (Game-Theoretic Mixed-Strategy Policy Portfolio Evaluation).
Constructs a portfolio of orthogonal deterministic expert profiles:
- Profile 1: Strawberry Titan (Variant D.1: 38 Strawberries, 8 Cows) - High-Yield Compounding
- Profile 2: Dairy Industrialist (28 Strawberries, 8 Cows + 4 Sheep) - Continuous Daily Cashflow
- Profile 3: Fast-Turnover Cash (34 Strawberries, 8 Cows, Accelerated Liquidation) - Maximum Solvency

Evaluates the Payoff Matrix and Mixed-Strategy Nash Equilibrium vs opponent population across 64 matches on 32 seeds.
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

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.agent import VariantDAgent

def make_portfolio_agent(profile_name: str):
    """Creates a deterministic profile instance within the portfolio."""
    def _act(obs, config=None):
        if profile_name == "DAIRY_INDUSTRIALIST":
            apex4_mod.configure_strategy({"cows": 8, "sheep": 4, "strawberries": 28})
        elif profile_name == "FAST_TURNOVER":
            apex4_mod.configure_strategy({"cows": 8, "strawberries": 34, "strawberry_last_plant": 16})
        else:
            apex4_mod.configure_strategy({"cows": 8, "sheep": 0, "strawberries": 38})

        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}

        base_act = apex4_mod.agent(obs, config)
        if not isinstance(base_act, dict):
            return base_act

        farmer_act = list(base_act.get("farmer") or ["PASS"])
        hands_act = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # Disciplined Selling (qty >= 4)
        for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
            qty = int(shed.get(item, 0) or 0)
            if qty >= 4:
                if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["SELL", item, qty])

        # Step 696 Clearance
        if step >= 696:
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = int(shed.get(item, 0) or 0)
                if qty > 0:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

        return {
            "farmer": farmer_act,
            "hands": hands_act,
            "market": market_orders[:10],
        }
    return _act

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
        "p90": float(np.percentile(arr, 90)),
    }

def run_exp038():
    print("=" * 105)
    print("EXP038: TRACK B (GAME-THEORETIC POLICY PORTFOLIO EVALUATION - 32 SEEDS / 64 MATCHES PER PROFILE)")
    print("=" * 105)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    profiles = [
        ("Profile 1: Strawberry Titan (Variant D.1)", "STRAWBERRY_TITAN"),
        ("Profile 2: Dairy Industrialist (Cows + Sheep)", "DAIRY_INDUSTRIALIST"),
        ("Profile 3: Fast-Turnover Cash (High Solvency)", "FAST_TURNOVER"),
    ]

    portfolio_results = []

    for name, p_key in profiles:
        banks = []
        wins = 0.0
        print(f"Evaluating {name} across 64 matches on 32 seeds...")
        for s in seeds:
            agent_fn = make_portfolio_agent(p_key)
            # Match 1: Cand = Seat 0, v18 = Seat 1
            env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env1.reset()
            while not env1.done:
                env1.step([agent_fn(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
            r_c_s0 = float(env1.state[0].reward or 0.0)
            r_v_s1 = float(env1.state[1].reward or 0.0)
            if r_c_s0 > r_v_s1: wins += 1.0
            elif r_c_s0 == r_v_s1: wins += 0.5

            # Match 2: v18 = Seat 0, Cand = Seat 1
            env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env2.reset()
            while not env2.done:
                env2.step([bot_v18.agent(env2.state[0].observation), agent_fn(env2.state[1].observation)])
            r_v_s0 = float(env2.state[0].reward or 0.0)
            r_c_s1 = float(env2.state[1].reward or 0.0)
            if r_c_s1 > r_v_s0: wins += 1.0
            elif r_c_s1 == r_v_s0: wins += 0.5

            banks.extend([r_c_s0, r_c_s1])

        st = compute_distribution_stats(banks)
        wr = wins / (len(seeds) * 2)
        portfolio_results.append({
            "name": name,
            "key": p_key,
            "stats": st,
            "win_rate": wr,
            "banks": banks,
        })
        print(f"  [DONE] {name:<45} -> Mean: ${st['mean']:>10,.2f} | Peak: ${st['max']:>10,.2f} | Win Rate: {wr:>6.1%}")

    print("\n" + "=" * 105)
    print("EXP038 POLICY PORTFOLIO PAYOFF & DISTRIBUTION MATRIX (64 MATCHES PER PROFILE)")
    print("=" * 105)
    print(f"{'Profile Name':<45} | {'Mean Bank':>12} | {'Median':>12} | {'Floor (Min)':>12} | {'Peak (Max)':>12} | {'Win Rate':>9}")
    print("-" * 105)

    for p in portfolio_results:
        st = p["stats"]
        print(f"{p['name']:<45} | ${st['mean']:>11,.2f} | ${st['median']:>11,.2f} | ${st['min']:>11,.2f} | ${st['max']:>11,.2f} | {p['win_rate']:>8.1%}")

    print("=" * 105)

if __name__ == "__main__":
    run_exp038()
