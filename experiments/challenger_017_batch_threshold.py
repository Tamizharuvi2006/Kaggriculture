"""Challenger 017: Multi-Product Selling Batch Threshold Sweep (qty >= 3 vs qty >= 4 vs qty >= 5).
Tests whether adjusting the dynamic selling batch threshold from 4 to 3 or 5 improves revenue over Variant D.1.
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

class Challenger017Agent:
    """Challenger 017: Configurable Selling Batch Threshold."""
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
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

            # Dynamic Selling with Parameterized Threshold
            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= self.threshold:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

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

def run_challenger_017_tournament():
    print("=" * 95)
    print("CHALLENGER 017: SELLING BATCH THRESHOLD SWEEP (QTY >= 3 and QTY >= 5 vs CONTROL QTY >= 4)")
    print("=" * 95)

    test_seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888
    ]

    ctrl = VariantDAgent()
    chal_3 = Challenger017Agent(threshold=3)
    chal_5 = Challenger017Agent(threshold=5)

    print(f"Simulating Challenger 017A (Threshold >= 3) vs Control (Threshold >= 4)...")
    report_3 = SeatSwapTournament.run_gauntlet(chal_3.act, ctrl.act, test_seeds, steps=720)

    print(f"Simulating Challenger 017B (Threshold >= 5) vs Control (Threshold >= 4)...")
    report_5 = SeatSwapTournament.run_gauntlet(chal_5.act, ctrl.act, test_seeds, steps=720)

    print("\n" + "=" * 95)
    print("CHALLENGER 017 THRESHOLD SWEEP RESULTS (16 SEEDS x 2 SEATS = 32 MATCHES)")
    print("=" * 95)
    print(f"Threshold >= 3 vs Control >= 4:")
    print(f"  - Win Rate           : {report_3['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate    : {report_3['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate    : {report_3['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin : ${report_3['mean_paired_delta']:+,.2f}")

    print(f"\nThreshold >= 5 vs Control >= 4:")
    print(f"  - Win Rate           : {report_5['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate    : {report_5['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate    : {report_5['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin : ${report_5['mean_paired_delta']:+,.2f}")

    print("\n" + "=" * 95)
    if report_3['overall_win_rate'] > 0.50 and report_3['mean_paired_delta'] > 20.0:
        print(">>> VERDICT: THRESHOLD >= 3 BEATS CONTROL! (PROMOTE TO D.2)")
    elif report_5['overall_win_rate'] > 0.50 and report_5['mean_paired_delta'] > 20.0:
        print(">>> VERDICT: THRESHOLD >= 5 BEATS CONTROL! (PROMOTE TO D.2)")
    else:
        print(">>> VERDICT: NEITHER THRESHOLD BEATS CONTROL >= 4! (CONFIRM THRESHOLD 4 IS OPTIMAL)")
    print("=" * 95)

if __name__ == "__main__":
    run_challenger_017_tournament()
