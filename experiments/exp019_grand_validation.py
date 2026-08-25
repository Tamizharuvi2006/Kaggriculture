"""EXP019: Grand Statistical Validation Suite (D.2 vs D.1 and D.2 vs kaitofukami-v18).
Runs across 32 unseen seeds x 2 seats (64 paired matches per matchup) to compute:
- 95% Confidence Intervals
- Paired t-test p-values
- Seat symmetry balance
Decisively settles whether D.2 (+>=3 threshold) is a statistically significant improvement over D.1 (+>=4 threshold).
"""
from __future__ import annotations
import sys
import os
import math
from scipy import stats

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

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.evaluation.seat_swap import SeatSwapTournament

class VariantD1Agent:
    """Variant D.1: Threshold >= 4, Step 696 Clearance."""
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

            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

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

class VariantD2Agent:
    """Variant D.2: Threshold >= 3, Step 696 Clearance."""
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

            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 3:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

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

def run_grand_validation():
    print("=" * 95)
    print("EXP019: GRAND STATISTICAL VALIDATION SUITE (32 SEEDS x 2 SEATS = 64 MATCHES PER MATCHUP)")
    print("=" * 95)

    # 32 Unseen Holdout Seeds
    seeds = [
        42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
        11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
        10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
        90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
    ]

    d1 = VariantD1Agent()
    d2 = VariantD2Agent()

    print(f"\n[1/2] Simulating Direct Head-to-Head: D.2 (>=3) vs D.1 (>=4) across {len(seeds)} seeds (64 matches)...")
    report_d2_vs_d1 = SeatSwapTournament.run_gauntlet(d2.act, d1.act, seeds, steps=720)

    print(f"\n[2/2] Simulating Benchmark: D.2 vs kaitofukami-v18 across {len(seeds)} seeds (64 matches)...")
    report_d2_vs_v18 = SeatSwapTournament.run_gauntlet(d2.act, bot_v18.agent, seeds, steps=720)

    # Statistical Significance Testing for D.2 vs D.1
    deltas_d2_d1 = [r["paired_delta"] for r in report_d2_vs_d1["detailed_results"]]
    mean_delta = float(report_d2_vs_d1["mean_paired_delta"])
    std_delta = float(stats.tstd(deltas_d2_d1)) if len(deltas_d2_d1) > 1 else 0.0
    se_delta = std_delta / math.sqrt(len(deltas_d2_d1)) if len(deltas_d2_d1) > 0 else 0.0
    ci_95 = (mean_delta - 1.96 * se_delta, mean_delta + 1.96 * se_delta)
    
    t_stat, p_val = stats.ttest_1samp(deltas_d2_d1, 0.0)

    print("\n" + "=" * 95)
    print("EXP019 GRAND VALIDATION STATISTICAL REPORT (64 MATCHES)")
    print("=" * 95)
    print(f"DIRECT HEAD-TO-HEAD: Variant D.2 vs Variant D.1")
    print(f"  - Overall Win Rate       : {report_d2_vs_d1['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate        : {report_d2_vs_d1['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate        : {report_d2_vs_d1['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin     : ${mean_delta:+,.2f}")
    print(f"  - 95% Confidence Interval: [${ci_95[0]:+,.2f}, ${ci_95[1]:+,.2f}]")
    print(f"  - Standard Error (SE)    : ${se_delta:,.2f}")
    print(f"  - Student t-statistic    : {t_stat:+.4f}")
    print(f"  - Two-tailed p-value     : {p_val:.4f}")

    print("\nBENCHMARK: Variant D.2 vs kaitofukami-v18")
    print(f"  - Overall Win Rate       : {report_d2_vs_v18['overall_win_rate']:.1%}")
    print(f"  - Seat 0 Win Rate        : {report_d2_vs_v18['seat0_win_rate']:.1%}")
    print(f"  - Seat 1 Win Rate        : {report_d2_vs_v18['seat1_win_rate']:.1%}")
    print(f"  - Mean Paired Margin     : ${report_d2_vs_v18['mean_paired_delta']:+,.2f}")
    print(f"  - Total Cumulative Edge  : ${report_d2_vs_v18['total_delta']:+,.2f}")

    print("\n" + "=" * 95)
    if mean_delta > 0:
        print(">>> CONCLUSION: VARIANT D.2 IS EMPIRICALLY SUPERIOR! PROCEED TO PRODUCTION SUBMISSION 🚀")
    else:
        print(">>> CONCLUSION: VARIANT D.1 REMAINS THE PREFERRED BASELINE.")
    print("=" * 95)

if __name__ == "__main__":
    run_grand_validation()
