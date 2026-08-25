"""EXP008: True Additive Factorial Component Matrix.
Systematically tests the isolated and combined impact of:
- A: Pure Baseline Spine
- B: Baseline + Dynamic Selling
- C: Baseline + Terminal Clearance (Step 700+)
- D: Baseline + Dynamic Selling + Terminal Clearance
- E: Baseline + Scarcity Pivot
- F: Full Stack (Baseline + Scarcity + Dynamic Selling + Terminal Clearance)
"""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

# 1. Load Baseline Bot (kaitofukami-v18)
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

# 2. Load Master APEX Spine
spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.state.observation import Observation
from engine.state.market_state import MarketTracker
from engine.state.farm_state import FarmState
from engine.state.opponent_state import OpponentState
from engine.strategy.scarcity_pivot import ScarcityPivotEngine
from engine.evaluation.tournament import TournamentEngine

class FactorialAgent:
    """Configurable agent to isolate individual additive mechanisms."""
    def __init__(
        self,
        use_dynamic_selling: bool = False,
        use_terminal_clearance: bool = False,
        use_scarcity_pivot: bool = False,
    ):
        self.use_dynamic_selling = use_dynamic_selling
        self.use_terminal_clearance = use_terminal_clearance
        self.use_scarcity_pivot = use_scarcity_pivot
        self.market_tracker = MarketTracker()

    def act(self, raw_obs, raw_config=None):
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)
            step = obs.step
            day = obs.day
            hour = obs.hour

            # Pure base action from master spine
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # Additive Layer 1: Scarcity Pivot (Seed Buying)
            if self.use_scarcity_pivot and 4 <= day <= 20:
                scarcity = ScarcityPivotEngine.evaluate_planting_choice(obs, farm, market, None, candidate_slot_count=4)
                if scarcity.chosen_crop in ("TOMATO", "CARROT"):
                    target_crop = scarcity.chosen_crop
                    if farm.seeds.get(target_crop, 0) < 4 and len(market_orders) < 9 and farm.money >= 3000.0:
                        market_orders.append(["BUY_SEED", target_crop, 4])

            # Additive Layer 2: Dynamic Selling (Pre-clearance selling into price spikes)
            if self.use_dynamic_selling:
                for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                    qty = farm.shed.get(item, 0)
                    if qty >= 4:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

            # Additive Layer 3: Terminal Endgame Clearance (Step >= 700)
            if self.use_terminal_clearance and step >= 700:
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

def run_factorial_matrix():
    print("=" * 95)
    print("EXP008: TRUE ADDITIVE FACTORIAL ABLATION MATRIX (8 SEEDS x 2 SEATS = 16 MATCHES/OPP)")
    print("=" * 95)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888]
    opponents = {
        "kaitofukami-v18 (Replay Champion)": bot_v18.agent,
    }

    variants = {
        "A. Baseline Spine Only": FactorialAgent(False, False, False),
        "B. Baseline + Dynamic Selling": FactorialAgent(True, False, False),
        "C. Baseline + Terminal Clearance": FactorialAgent(False, True, False),
        "D. Baseline + DynSell + TermClear": FactorialAgent(True, True, False),
        "E. Baseline + Scarcity Pivot": FactorialAgent(False, False, True),
        "F. Full Stack (Base + Scarcity + DynSell + Clear)": FactorialAgent(True, True, True),
    }

    results = {}
    for name, agent_obj in variants.items():
        print(f"\nSimulating Variant: {name}...")
        report = TournamentEngine.run_multi_opponent_gauntlet(agent_obj.act, opponents, test_seeds, steps=720)
        results[name] = report

    print("\n" + "=" * 95)
    print("EXP008 FACTORIAL RESULTS AGAINST kaitofukami-v18")
    print("=" * 95)
    print(f"{'Variant':<48} | {'Win Rate':>10} | {'Seat 0 Win%':>12} | {'Seat 1 Win%':>12} | {'Mean Paired Delta':>18}")
    print("-" * 105)

    for name, report in results.items():
        stats = report["opponents"]["kaitofukami-v18 (Replay Champion)"]
        print(f"{name:<48} | {stats['overall_win_rate']:>9.1%} | {stats['seat0_win_rate']:>11.1%} | {stats['seat1_win_rate']:>11.1%} | ${stats['mean_paired_delta']:>+17,.2f}")

if __name__ == "__main__":
    run_factorial_matrix()
