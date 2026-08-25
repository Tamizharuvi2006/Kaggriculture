"""Challenger 013: Precise Day 30 (Step 696) Full Endgame Clearance.
Tests whether initiating terminal liquidation at Step 696 (beginning of final day) beats Step 700.
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
from engine.evaluation.seat_swap import SeatSwapTournament

class Challenger013Agent:
    """Challenger 013: Early Day 30 (Step 696) Terminal Clearance Engine."""
    def __init__(self):
        self.market_tracker = MarketTracker()

    def reset(self):
        self.market_tracker.reset()

    def act(self, raw_obs, raw_config=None):
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)
            step = obs.step

            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # Dynamic Selling (Standard Variant D)
            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

            # Challenger 013: Trigger Terminal Clearance at Step 696 (Start of Day 30)
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

def run_challenger_013_tournament():
    print("=" * 95)
    print("CHALLENGER 013: DAY 30 (STEP 696) TERMINAL CLEARANCE vs VARIANT D CONTROL")
    print("=" * 95)

    test_seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888
    ]

    ctrl = VariantDAgent()
    chal = Challenger013Agent()

    print(f"Simulating Head-to-Head Tournament across {len(test_seeds)} seeds (32 paired matches)...")
    report_h2h = SeatSwapTournament.run_gauntlet(chal.act, ctrl.act, test_seeds, steps=720)

    print("\nSimulating Benchmark vs kaitofukami-v18 across 32 paired matches...")
    report_vs_v18_chal = SeatSwapTournament.run_gauntlet(chal.act, bot_v18.agent, test_seeds, steps=720)
    report_vs_v18_ctrl = SeatSwapTournament.run_gauntlet(ctrl.act, bot_v18.agent, test_seeds, steps=720)

    print("\n" + "=" * 95)
    print("CHALLENGER 013 TOURNAMENT RESULTS (16 SEEDS x 2 SEATS = 32 MATCHES)")
    print("=" * 95)
    print(f"Direct Matchup: Challenger 013 (Step 696) vs Variant D Control (Step 700)")
    print(f"  - Challenger Win Rate: {report_h2h['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate    : {report_h2h['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate    : {report_h2h['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin : ${report_h2h['mean_paired_delta']:+,.2f}")
    print(f"  - Total Delta        : ${report_h2h['total_delta']:+,.2f}")

    print("\nBenchmark vs kaitofukami-v18:")
    print(f"  - Variant D Control Win Rate : {report_vs_v18_ctrl['overall_win_rate']:.1%} | Margin: ${report_vs_v18_ctrl['mean_paired_delta']:+,.2f}")
    print(f"  - Challenger 013 Win Rate    : {report_vs_v18_chal['overall_win_rate']:.1%} | Margin: ${report_vs_v18_chal['mean_paired_delta']:+,.2f}")

    print("\n" + "=" * 95)
    if report_h2h['overall_win_rate'] >= 0.50 and report_h2h['mean_paired_delta'] > 20.0:
        print(">>> VERDICT: CHALLENGER 013 BEATS VARIANT D! (PROMOTE TO NEW CHAMPION)")
    else:
        print(">>> VERDICT: CHALLENGER 013 FAILS TO BEAT VARIANT D! (KEEP VARIANT D)")
    print("=" * 95)

if __name__ == "__main__":
    run_challenger_013_tournament()
