"""EXP026: Fast Direct Macro-Economic Factorial Comparison (64 Matches Total).
Directly tests the 4 most promising livestock/crop candidate configurations:
1. Control (Variant D.1): 8 Cows, 0 Melons (Pure 38-Strawberry Spine)
2. High-Milk Engine: 12 Cows, 0 Melons
3. Balanced Multi-Product: 10 Cows, 2 Melons
4. Dense Multi-Product: 12 Cows, 4 Melons
"""
from __future__ import annotations
import sys
import os
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

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker

class ParameterizedAgent:
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

            # Parameterized Livestock
            cows_count = len(farm.animals_by_type.get("COW", []))
            if cows_count < self.target_cows and n_unlocked >= 3 and 14 <= day <= 20 and farm.money >= 3500.0:
                if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_ANIMAL", "COW"])

            # Parameterized Melons
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

            # Step 696 Clearance
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

def run_direct_sweep():
    print("=" * 95)
    print("EXP026: DIRECT FACTORIAL EVALUATION (4 CONFIGURATIONS x 16 MATCHES = 64 MATCHES)")
    print("=" * 95)

    seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 22222]

    configs = [
        ("Control (D.1): 8 Cows, 0 Melons", 8, 0),
        ("High-Milk: 12 Cows, 0 Melons", 12, 0),
        ("Balanced: 10 Cows, 2 Melons", 10, 2),
        ("Dense Multi: 12 Cows, 4 Melons", 12, 4),
    ]

    results = []

    for name, c_tgt, m_tgt in configs:
        cand_banks = []
        wins = 0.0
        for s in seeds:
            # Match 1: Cand = Seat 0, v18 = Seat 1
            env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env1.reset()
            a1 = ParameterizedAgent(c_tgt, m_tgt)
            while not env1.done:
                env1.step([a1.act(env1.state[0].observation), bot_v18.agent(env1.state[1].observation)])
            r_c_s0 = float(env1.state[0].reward or 0.0)
            r_v_s1 = float(env1.state[1].reward or 0.0)
            if r_c_s0 > r_v_s1: wins += 1.0
            elif r_c_s0 == r_v_s1: wins += 0.5

            # Match 2: v18 = Seat 0, Cand = Seat 1
            env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
            env2.reset()
            a2 = ParameterizedAgent(c_tgt, m_tgt)
            while not env2.done:
                env2.step([bot_v18.agent(env2.state[0].observation), a2.act(env2.state[1].observation)])
            r_v_s0 = float(env2.state[0].reward or 0.0)
            r_c_s1 = float(env2.state[1].reward or 0.0)
            if r_c_s1 > r_v_s0: wins += 1.0
            elif r_c_s1 == r_v_s0: wins += 0.5

            cand_banks.extend([r_c_s0, r_c_s1])

        mean_b = float(np.mean(cand_banks))
        med_b = float(np.median(cand_banks))
        max_b = float(np.max(cand_banks))
        min_b = float(np.min(cand_banks))
        win_r = wins / (len(seeds) * 2)

        results.append({
            "name": name,
            "cows": c_tgt, "melons": m_tgt,
            "mean": mean_b, "median": med_b, "max": max_b, "min": min_b,
            "win_rate": win_r,
        })
        print(f"  [DONE] {name:<35} -> Mean: ${mean_b:>10,.2f} | Peak: ${max_b:>10,.2f} | Win%: {win_r:>6.1%}")

    print("\n" + "=" * 95)
    print("EXP026 FACTORIAL EVALUATION REPORT (16 Matches per Candidate)")
    print("=" * 95)
    print(f"{'Configuration':<35} | {'Mean Bank':>14} | {'Median Bank':>14} | {'Peak Bank':>14} | {'Floor Bank':>14} | {'Win Rate vs v18':>18}")
    print("-" * 95)

    for r in results:
        print(f"{r['name']:<35} | ${r['mean']:>13,.2f} | ${r['median']:>13,.2f} | ${r['max']:>13,.2f} | ${r['min']:>13,.2f} | {r['win_rate']:>17.1%}")

    best_mean = max(results, key=lambda x: x["mean"])
    print("\n" + "=" * 95)
    print(f"🏆 TOP ECONOMIC CONFIGURATION: {best_mean['name']} -> Mean: ${best_mean['mean']:,.2f} | Peak: ${best_mean['max']:,.2f} | Win%: {best_mean['win_rate']:.1%}")
    print("=" * 95)

if __name__ == "__main__":
    run_direct_sweep()
