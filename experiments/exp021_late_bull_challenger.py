"""EXP021: Late Bull-Market Regime Gated Challenger.
Tests whether a strictly gated late-game (Day >= 22) bull-market hold filter
can capture the tail-upside on mega-bull seeds (e.g. Seed 22222, 777777)
without degrading the 90.6% generalist win rate across normal seeds.
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

class LateBullChallengerAgent:
    """Variant D.1 with Strictly Gated Late-Bull Market Hold Logic."""
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
            day = obs.day

            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # Gated Late-Bull Detection Conditions (Days 22-28):
            p_straw = market.price("STRAWBERRY")
            v_straw = market.velocity("STRAWBERRY")
            p_milk = market.price("MILK")
            v_milk = market.velocity("MILK")

            is_late_game = (22 <= day <= 28)
            is_hyper_solvent = (farm.money >= 35000.0)
            shed_total = sum(farm.shed.values())
            has_capacity = (shed_total <= 65)

            # Strict Late-Bull Strawberry Hold:
            # If late game, super rich, lots of shed room, and price is surging upwards (>135 and velocity > 0)
            # allow holding until 8 units or price reaches peak >= 150.
            is_bull_straw = (is_late_game and is_hyper_solvent and has_capacity and p_straw >= 135.0 and v_straw >= 0)
            straw_sell_threshold = 8 if (is_bull_straw and p_straw < 150.0) else 4

            straw_qty = farm.shed.get("STRAWBERRY", 0)
            if straw_qty >= straw_sell_threshold:
                if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["SELL", "STRAWBERRY", straw_qty])

            # Strict Late-Bull Milk Hold:
            is_bull_milk = (is_late_game and is_hyper_solvent and has_capacity and p_milk >= 150.0 and v_milk >= 0)
            milk_sell_threshold = 8 if (is_bull_milk and p_milk < 185.0) else 4

            milk_qty = farm.shed.get("MILK", 0)
            if milk_qty >= milk_sell_threshold:
                if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["SELL", "MILK", milk_qty])

            # Other sellables (standard threshold 4)
            for item in ("TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
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

def run_exp021_tournament():
    print("=" * 95)
    print("EXP021: LATE BULL-MARKET GATED CHALLENGER vs VARIANT D.1 (64 MATCHES ON 32 SEEDS)")
    print("=" * 95)

    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    ctrl = VariantDAgent()
    chal = LateBullChallengerAgent()

    print(f"\n[1/3] Simulating Direct Head-to-Head: Late-Bull Challenger vs Variant D.1 Control...")
    report_h2h = SeatSwapTournament.run_gauntlet(chal.act, ctrl.act, seeds, steps=720)

    print(f"\n[2/3] Simulating Challenger vs kaitofukami-v18 across 64 matches...")
    report_vs_v18_chal = SeatSwapTournament.run_gauntlet(chal.act, bot_v18.agent, seeds, steps=720)

    print(f"\n[3/3] Simulating Control vs kaitofukami-v18 across 64 matches...")
    report_vs_v18_ctrl = SeatSwapTournament.run_gauntlet(ctrl.act, bot_v18.agent, seeds, steps=720)

    print("\n" + "=" * 95)
    print("EXP021 TOURNAMENT METRICS (64 MATCHES / 32 UNSEEN SEEDS)")
    print("=" * 95)
    print(f"Direct Matchup: Late-Bull Challenger vs Variant D.1 Control")
    print(f"  - Challenger Win Rate: {report_h2h['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate    : {report_h2h['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate    : {report_h2h['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin : ${report_h2h['mean_paired_delta']:+,.2f}")
    print(f"  - Total Delta        : ${report_h2h['total_delta']:+,.2f}")

    print("\nBenchmark Comparison vs kaitofukami-v18:")
    print(f"  - Variant D.1 Control Win Rate : {report_vs_v18_ctrl['overall_win_rate']:.1%} | Margin: ${report_vs_v18_ctrl['mean_paired_delta']:+,.2f} | Total: ${report_vs_v18_ctrl['total_delta']:+,.2f}")
    print(f"  - Late-Bull Challenger Win Rate: {report_vs_v18_chal['overall_win_rate']:.1%} | Margin: ${report_vs_v18_chal['mean_paired_delta']:+,.2f} | Total: ${report_vs_v18_chal['total_delta']:+,.2f}")

    # Inspect Specific Bull Seeds (22222 and 777777)
    print("\n" + "-" * 95)
    print("SPECIFIC LOSS SEED VERIFICATION (Seed 22222 and Seed 777777):")
    for r in report_vs_v18_chal["detailed_results"]:
        if r["seed"] in (22222, 777777):
            print(f"  - Seed {r['seed']:6d}: Challenger Paired Delta = ${r['paired_delta']:+,.2f} (Match 1: ${r['cand_seat0'] - r['ctrl_seat1']:+,.2f}, Match 2: ${r['cand_seat1'] - r['ctrl_seat0']:+,.2f})")

    print("\n" + "=" * 95)
    if report_vs_v18_chal['overall_win_rate'] >= report_vs_v18_ctrl['overall_win_rate'] and report_h2h['mean_paired_delta'] > 20.0:
        print(">>> VERDICT: LATE-BULL CHALLENGER BEATS VARIANT D.1! (PROMOTE TO D.3)")
    else:
        print(">>> VERDICT: LATE-BULL CHALLENGER DOES NOT STRICTLY DOMINATE D.1! (KEEP VARIANT D.1)")
    print("=" * 95)

if __name__ == "__main__":
    run_exp021_tournament()
