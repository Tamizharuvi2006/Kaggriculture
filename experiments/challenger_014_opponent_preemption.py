"""Challenger 014: Opponent-Aware Market Dump Preemption.
Tests whether preempting expected opponent inventory dumps by selling before price crashes beats Variant D.1.
"""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.state.opponent_state import OpponentState
from engine.evaluation.seat_swap import SeatSwapTournament

class Challenger014Agent:
    """Challenger 014: Variant D.1 + Opponent Dump Preemption."""
    def __init__(self):
        self.market_tracker = MarketTracker()
        self.prev_opp = None

    def reset(self):
        self.market_tracker.reset()
        self.prev_opp = None

    def act(self, raw_obs, raw_config=None):
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)
            opponent = OpponentState(obs, self.prev_opp)
            self.prev_opp = opponent
            step = obs.step

            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # Standard Variant D Selling: Inventory >= 4
            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

            # Challenger 014: Preempt Opponent Imminent Dumps (when shed has 2 or 3 items)
            for item, opp_inv in opponent.inventory.items():
                if opp_inv.dump_probability >= 0.70:
                    our_qty = farm.shed.get(item, 0)
                    if 2 <= our_qty < 4:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, our_qty])

            # Terminal Endgame Clearance (Step >= 696)
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

def run_challenger_014_tournament():
    print("=" * 95)
    print("CHALLENGER 014: OPPONENT DUMP PREEMPTION vs VARIANT D.1 CONTROL")
    print("=" * 95)

    test_seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888
    ]

    ctrl = VariantDAgent()
    chal = Challenger014Agent()

    print(f"Simulating Head-to-Head Tournament across {len(test_seeds)} seeds (32 paired matches)...")
    report_h2h = SeatSwapTournament.run_gauntlet(chal.act, ctrl.act, test_seeds, steps=720)

    print("\nSimulating Benchmark vs kaitofukami-v18 across 32 paired matches...")
    report_vs_v18_chal = SeatSwapTournament.run_gauntlet(chal.act, bot_v18.agent, test_seeds, steps=720)
    report_vs_v18_ctrl = SeatSwapTournament.run_gauntlet(ctrl.act, bot_v18.agent, test_seeds, steps=720)

    print("\n" + "=" * 95)
    print("CHALLENGER 014 TOURNAMENT RESULTS (16 SEEDS x 2 SEATS = 32 MATCHES)")
    print("=" * 95)
    print(f"Direct Matchup: Challenger 014 (Preemption) vs Variant D.1 Control")
    print(f"  - Challenger Win Rate: {report_h2h['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate    : {report_h2h['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate    : {report_h2h['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin : ${report_h2h['mean_paired_delta']:+,.2f}")
    print(f"  - Total Delta        : ${report_h2h['total_delta']:+,.2f}")

    print("\nBenchmark vs kaitofukami-v18:")
    print(f"  - Variant D.1 Control Win Rate : {report_vs_v18_ctrl['overall_win_rate']:.1%} | Margin: ${report_vs_v18_ctrl['mean_paired_delta']:+,.2f}")
    print(f"  - Challenger 014 Win Rate      : {report_vs_v18_chal['overall_win_rate']:.1%} | Margin: ${report_vs_v18_chal['mean_paired_delta']:+,.2f}")

    print("\n" + "=" * 95)
    if report_h2h['overall_win_rate'] > 0.50 and report_h2h['mean_paired_delta'] > 20.0:
        print(">>> VERDICT: CHALLENGER 014 BEATS VARIANT D.1! (PROMOTE TO NEW CHAMPION)")
    else:
        print(">>> VERDICT: CHALLENGER 014 FAILS TO BEAT VARIANT D.1! (KEEP VARIANT D.1)")
    print("=" * 95)

if __name__ == "__main__":
    run_challenger_014_tournament()
