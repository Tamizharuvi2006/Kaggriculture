"""EXP009: Experimental Head-to-Head Challenger Tournament.
Variant D (Locked Control) vs Variant D + Monte Carlo Search (Challenger) vs kaitofukami-v18.
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

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.search.monte_carlo import MonteCarloOverrideEngine
from engine.evaluation.tournament import TournamentEngine

class VariantDWithMCOverrideAgent:
    """Challenger: Variant D with Monte Carlo Search Overrides."""
    def __init__(self, min_override_margin: float = 150.0):
        self.base_d = VariantDAgent()
        self.min_override_margin = min_override_margin

    def reset(self):
        self.base_d.reset()

    def act(self, raw_obs, raw_config=None):
        base_d_action = self.base_d.act(raw_obs, raw_config)
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.base_d.market_tracker.update(obs)
            
            # Apply MC evaluation override if EV strictly exceeds Variant D
            final_action = MonteCarloOverrideEngine.evaluate_decision_overrides(
                obs=obs,
                farm=farm,
                market=market,
                variant_d_action=base_d_action,
                min_override_margin=self.min_override_margin,
            )
            return final_action
        except Exception:
            return base_d_action

def run_exp009():
    print("=" * 95)
    print("EXP009: VARIANT D (CONTROL) vs VARIANT D + MONTE CARLO (CHALLENGER)")
    print("=" * 95)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888, 11111, 22222, 33333, 44444]
    opponents = {
        "kaitofukami-v18 (Replay Champion)": bot_v18.agent,
    }

    # 1. Run Control (Variant D)
    print("\nSimulating Control: Variant D (Locked Control)...")
    ctrl_agent = VariantDAgent()
    report_ctrl = TournamentEngine.run_multi_opponent_gauntlet(ctrl_agent.act, opponents, test_seeds, steps=720)

    # 2. Run Challenger (Variant D + MC)
    print("\nSimulating Challenger: Variant D + Monte Carlo Search...")
    chal_agent = VariantDWithMCOverrideAgent(min_override_margin=150.0)
    report_chal = TournamentEngine.run_multi_opponent_gauntlet(chal_agent.act, opponents, test_seeds, steps=720)

    # 3. Direct Head-to-Head: Variant D + MC vs Variant D
    print("\nSimulating Direct Head-to-Head: Challenger vs Control...")
    from engine.evaluation.seat_swap import SeatSwapTournament
    report_h2h = SeatSwapTournament.run_gauntlet(chal_agent.act, ctrl_agent.act, test_seeds, steps=720)

    print("\n" + "=" * 95)
    print("EXP009 FINAL TOURNAMENT COMPARISON (12 SEEDS x 2 SEATS = 24 MATCHES PER OPPONENT)")
    print("=" * 95)
    
    stats_ctrl = report_ctrl["opponents"]["kaitofukami-v18 (Replay Champion)"]
    stats_chal = report_chal["opponents"]["kaitofukami-v18 (Replay Champion)"]

    print(f"{'System':<35} | {'Win% vs v18':>12} | {'Seat 0 Win%':>12} | {'Seat 1 Win%':>12} | {'Mean Paired Delta':>18}")
    print("-" * 100)
    print(f"{'Variant D (Control)':<35} | {stats_ctrl['overall_win_rate']:>11.1%} | {stats_ctrl['seat0_win_rate']:>11.1%} | {stats_ctrl['seat1_win_rate']:>11.1%} | ${stats_ctrl['mean_paired_delta']:>+17,.2f}")
    print(f"{'Variant D + MC Search (Challenger)':<35} | {stats_chal['overall_win_rate']:>11.1%} | {stats_chal['seat0_win_rate']:>11.1%} | {stats_chal['seat1_win_rate']:>11.1%} | ${stats_chal['mean_paired_delta']:>+17,.2f}")

    print("\n" + "-" * 100)
    print("DIRECT HEAD-TO-HEAD MATCHUP (Variant D + MC vs Variant D):")
    print(f"  Challenger Win Rate: {report_h2h['overall_win_rate']:.1%}")
    print(f"  Seat 0 Win Rate    : {report_h2h['seat0_win_rate']:.1%}")
    print(f"  Seat 1 Win Rate    : {report_h2h['seat1_win_rate']:.1%}")
    print(f"  Mean Paired Margin : ${report_h2h['mean_paired_delta']:+,.2f}")

if __name__ == "__main__":
    run_exp009()
