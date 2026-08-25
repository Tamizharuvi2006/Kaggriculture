"""EXP026: Multi-Core Factorial Sweep (Cows x Melons in 3-Quadrant Footprint).
Evaluates Cows: [8, 10, 12, 14] x Melons: [0, 2, 4] across 16 holdout seeds (32 matches per cell).
Uses multiprocessing.Pool for true 100% multi-core CPU parallelism.
"""
from __future__ import annotations
import sys
import os
import json
import numpy as np
import multiprocessing

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def _eval_single_config(cows: int, melons: int, seeds: list[int]) -> dict:
    import kaggle_environments
    import importlib.util

    spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
    bot_v18 = importlib.util.module_from_spec(spec_v18)
    spec_v18.loader.exec_module(bot_v18)

    spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
    apex4_mod = importlib.util.module_from_spec(spec_apex4)
    spec_apex4.loader.exec_module(apex4_mod)

    from engine.state.observation import Observation
    from engine.state.farm_state import FarmState
    from engine.state.market_state import MarketTracker

    class SweepAgent:
        def __init__(self):
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

                # Livestock Scaling
                cows_count = len(farm.animals_by_type.get("COW", []))
                if cows_count < cows and n_unlocked >= 3 and 14 <= day <= 20 and farm.money >= 3500.0:
                    if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["BUY_ANIMAL", "COW"])

                # Melon Scaling
                if melons > 0 and n_unlocked >= 3 and 12 <= day <= 20 and farm.money >= 1200.0:
                    melon_seeds = farm.seeds.get("MELON", 0)
                    if melon_seeds < melons and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", melons])

                # Disciplined Selling
                for item in ("STRAWBERRY", "MILK", "MELON", "TOMATO", "CARROT", "WOOL"):
                    qty = farm.shed.get(item, 0)
                    if qty >= 4:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

                # Terminal Clearance
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
        a1 = SweepAgent()
        while not env1.done:
            env1.step([a1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
        r_c_s0 = float(env1.state[0].reward or 0.0)
        r_v_s1 = float(env1.state[1].reward or 0.0)
        if r_c_s0 > r_v_s1: wins += 1.0
        elif r_c_s0 == r_v_s1: wins += 0.5

        # Match 2: v18 = Seat 0, Cand = Seat 1
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
        env2.reset()
        a2 = SweepAgent()
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

def _wrapper(args):
    return _eval_single_config(*args)

def main():
    print("=" * 95)
    print("EXP026: MULTI-CORE FACTORIAL SWEEP (Cows: [8, 10, 12, 14] x Melons: [0, 2, 4])")
    print("=" * 95)

    seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
             11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888]

    configs = []
    for c in [8, 10, 12, 14]:
        for m in [0, 2, 4]:
            configs.append((c, m, seeds))

    print(f"Executing {len(configs)} configurations across multiprocessing worker pool...")
    with multiprocessing.Pool(processes=min(12, os.cpu_count() or 4)) as pool:
        results = pool.map(_wrapper, configs)

    print("\n" + "=" * 95)
    print("EXP026 FACTORIAL GRID SWEEP RESULTS (16 Seeds x 2 Seats = 32 Matches per Cell)")
    print("=" * 95)
    print(f"{'Cows':<6} | {'Melons':<8} | {'Mean Bank':>14} | {'Median Bank':>14} | {'Max Bank':>14} | {'Min Bank':>14} | {'Win Rate vs v18':>18}")
    print("-" * 95)

    for r in results:
        print(f"{r['cows']:<6d} | {r['melons']:<8d} | ${r['mean']:>13,.2f} | ${r['median']:>13,.2f} | ${r['max']:>13,.2f} | ${r['min']:>13,.2f} | {r['win_rate']:>17.1%}")

    best_mean = max(results, key=lambda x: x["mean"])
    best_win = max(results, key=lambda x: x["win_rate"])

    print("\n" + "=" * 95)
    print(f"🏆 HIGHEST AVERAGE WEALTH CONFIG: {best_mean['cows']} Cows, {best_mean['melons']} Melons -> Mean: ${best_mean['mean']:,.2f} | Peak: ${best_mean['max']:,.2f} | Win%: {best_mean['win_rate']:.1%}")
    print(f"🏆 HIGHEST TOURNAMENT WIN RATE  : {best_win['cows']} Cows, {best_win['melons']} Melons -> Win%: {best_win['win_rate']:.1%} | Mean: ${best_win['mean']:,.2f}")
    print("=" * 95)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
