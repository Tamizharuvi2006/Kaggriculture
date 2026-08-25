"""EXP026: Ultra-Fast Parallel Factorial Sweep (Cows x Melons in 3 Quadrants).
16 Dedicated Cell Workers running across all CPU cores.
Evaluates 16 macroeconomic configurations across 32 holdout seeds (1,024 matches total).
"""
from __future__ import annotations
import sys
import os
import concurrent.futures
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

def _eval_cell_batch(args: tuple) -> dict:
    """Evaluates an entire (cows, melons) cell across all 32 seeds in a single process."""
    cows, melons, seeds = args

    # Load baseline bot
    spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
    bot_v18 = importlib.util.module_from_spec(spec_v18)
    spec_v18.loader.exec_module(bot_v18)

    # Load APEX spine
    spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
    apex4_mod = importlib.util.module_from_spec(spec_apex4)
    spec_apex4.loader.exec_module(apex4_mod)

    from engine.state.observation import Observation
    from engine.state.farm_state import FarmState
    from engine.state.market_state import MarketTracker

    class ConfigAgent:
        def __init__(self, target_cows: int, target_melons: int):
            self.target_cows = target_cows
            self.target_melons = target_melons
            self.market_tracker = MarketTracker()

        def act(self, raw_obs, raw_config=None):
            try:
                obs = Observation(raw_obs, raw_config)
                farm = FarmState(obs)
                market = self.market_tracker.update(obs)
                step = obs.step
                day = obs.day
                n_unlocked = len(farm.unlocked_quadrants)

                base_act = apex4_mod.agent(raw_obs, raw_config)
                if not isinstance(base_act, dict):
                    return base_act

                farmer_act = list(base_act.get("farmer") or ["PASS"])
                hands_act = [list(h) for h in (base_act.get("hands") or [])]
                market_orders = list(base_act.get("market") or [])

                # Parameterized Livestock Scaling
                cows_count = len(farm.animals_by_type.get("COW", []))
                if cows_count < self.target_cows and n_unlocked >= 3 and 14 <= day <= 20 and farm.money >= 3500.0:
                    if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["BUY_ANIMAL", "COW"])

                # Parameterized Melon Injections
                if self.target_melons > 0 and n_unlocked >= 3 and 12 <= day <= 20 and farm.money >= 1200.0:
                    melon_seeds = farm.seeds.get("MELON", 0)
                    if melon_seeds < self.target_melons and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", self.target_melons])

                # Disciplined Selling
                for item in ("STRAWBERRY", "MILK", "MELON", "TOMATO", "CARROT", "WOOL"):
                    qty = farm.shed.get(item, 0)
                    if qty >= 4:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

                # Day 30 Clearance
                if step >= 696:
                    for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                        qty = farm.shed.get(item, 0)
                        if qty > 0:
                            if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                                if len(market_orders) < 10:
                                    market_orders.append(["SELL", item, qty])

                return {
                    "farmer": farmer_act,
                    "hands": hands_act,
                    "market": market_orders[:10],
                }
            except Exception:
                return apex4_mod.agent(raw_obs, raw_config)

    cand_banks = []
    wins = 0.0

    for s in seeds:
        # Match 1: Cand = Seat 0, v18 = Seat 1
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env1.reset()
        a1 = ConfigAgent(cows, melons)
        while not env1.done:
            env1.step([a1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        r_c_s0 = float(env1.state[0].reward or 0.0)
        r_v_s1 = float(env1.state[1].reward or 0.0)
        if r_c_s0 > r_v_s1: wins += 1.0
        elif r_c_s0 == r_v_s1: wins += 0.5

        # Match 2: v18 = Seat 0, Cand = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        a2 = ConfigAgent(cows, melons)
        while not env2.done:
            env2.step([bot_v18.agent(env2.state[0].observation), a2.act(env2.state[1].observation)])
        r_v_s0 = float(env2.state[0].reward or 0.0)
        r_c_s1 = float(env2.state[1].reward or 0.0)
        if r_c_s1 > r_v_s0: wins += 1.0
        elif r_c_s1 == r_v_s0: wins += 0.5

        cand_banks.extend([r_c_s0, r_c_s1])

    return {
        "cows": cows,
        "melons": melons,
        "mean": float(np.mean(cand_banks)),
        "median": float(np.median(cand_banks)),
        "max": float(np.max(cand_banks)),
        "min": float(np.min(cand_banks)),
        "win_rate": wins / (len(seeds) * 2),
    }

def run_factorial_sweep():
    print("=" * 95)
    print("EXP026: ULTRA-FAST PARALLEL FACTORIAL SWEEP (16 CONFIGS x 64 MATCHES = 1,024 MATCHES)")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    cow_options = [8, 10, 12, 14]
    melon_options = [0, 2, 4, 6]

    cell_tasks = []
    for c in cow_options:
        for m in melon_options:
            cell_tasks.append((c, m, seeds))

    max_workers = min(16, os.cpu_count() or 8)
    print(f"Executing 16 configuration cells concurrently across {max_workers} CPU cores...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for res in executor.map(_eval_cell_batch, cell_tasks):
            results.append(res)
            print(f"  [DONE] Cell ({res['cows']} Cows, {res['melons']} Melons) -> Mean: ${res['mean']:,.2f} | Win Rate: {res['win_rate']:.1%}")

    # Sort results
    results.sort(key=lambda x: (x["cows"], x["melons"]))

    print("\n" + "=" * 95)
    print("EXP026 FINAL FACTORIAL GRID SWEEP REPORT (32 SEEDS x 2 SEATS = 64 MATCHES PER CELL)")
    print("=" * 95)
    print(f"{'Cows':<6} | {'Melons':<8} | {'Mean Bank':>14} | {'Median Bank':>14} | {'Max Bank':>14} | {'Min Bank':>14} | {'Win Rate vs v18':>18}")
    print("-" * 95)

    for r in results:
        print(f"{r['cows']:<6d} | {r['melons']:<8d} | ${r['mean']:>13,.2f} | ${r['median']:>13,.2f} | ${r['max']:>13,.2f} | ${r['min']:>13,.2f} | {r['win_rate']:>17.1%}")

    best_mean = max(results, key=lambda x: x["mean"])
    best_win = max(results, key=lambda x: x["win_rate"])

    print("\n" + "=" * 95)
    print(f"🏆 HIGHEST AVERAGE WEALTH CONFIGURATION: {best_mean['cows']} Cows, {best_mean['melons']} Melons -> Mean: ${best_mean['mean']:,.2f} | Peak: ${best_mean['max']:,.2f} | Win%: {best_mean['win_rate']:.1%}")
    print(f"🏆 HIGHEST TOURNAMENT WIN RATE CONFIG  : {best_win['cows']} Cows, {best_win['melons']} Melons -> Win%: {best_win['win_rate']:.1%} | Mean: ${best_win['mean']:,.2f}")
    print("=" * 95)

if __name__ == "__main__":
    run_factorial_sweep()
