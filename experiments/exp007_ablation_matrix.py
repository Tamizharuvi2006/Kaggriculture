"""EXP007: Comprehensive 5-Way System Ablation Matrix across 4 Opponent Archetypes.
Isolates the exact marginal value contributed by each architectural subsystem:
- A. Full Adaptive Engine
- B. Minus Scarcity Pivot
- C. Minus Dynamic Selling
- D. Minus Opponent Counter
- E. Baseline Spine Only
"""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

from engine.agent import AdaptiveAgent
from baseline.challengers import carrot_rusher_agent, livestock_rusher_agent

spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_v83 = importlib.util.spec_from_file_location("bot_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
bot_v83 = importlib.util.module_from_spec(spec_v83)
spec_v83.loader.exec_module(bot_v83)

from engine.evaluation.tournament import TournamentEngine

def run_ablation_matrix():
    print("=" * 95)
    print("EXP007: 5-WAY SYSTEM ABLATION MATRIX (PAIRED SEATS ACROSS 8 SEEDS)")
    print("=" * 95)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888]
    opponents = {
        "kaitofukami-v18": bot_v18.agent,
        "submission_v83": bot_v83.agent,
        "Carrot Rusher": carrot_rusher_agent,
        "Livestock Rusher": livestock_rusher_agent,
    }

    variants = {
        "1. Full Adaptive Engine": lambda: AdaptiveAgent(
            enable_scarcity_pivot=True, enable_dynamic_selling=True, enable_opponent_counter=True
        ).act,
        "2. Minus Scarcity Pivot": lambda: AdaptiveAgent(
            enable_scarcity_pivot=False, enable_dynamic_selling=True, enable_opponent_counter=True
        ).act,
        "3. Minus Dynamic Selling": lambda: AdaptiveAgent(
            enable_scarcity_pivot=True, enable_dynamic_selling=False, enable_opponent_counter=True
        ).act,
        "4. Minus Opponent Counter": lambda: AdaptiveAgent(
            enable_scarcity_pivot=True, enable_dynamic_selling=True, enable_opponent_counter=False
        ).act,
        "5. Baseline Spine Only": lambda: bot_v18.agent,
    }

    ablation_results = {}
    for var_name, var_builder in variants.items():
        print(f"\nEvaluating: {var_name}...")
        report = TournamentEngine.run_multi_opponent_gauntlet(var_builder(), opponents, test_seeds, steps=720)
        ablation_results[var_name] = report

    print("\n" + "=" * 95)
    print("FINAL ABLATION COMPARISON TABLE (Composite Win Rate & Paired Deltas)")
    print("=" * 95)
    print(f"{'Variant':<28} | {'Overall Win%':>12} | {'v18 Margin':>12} | {'v83 Margin':>12} | {'Carrot Margin':>14} | {'Livestock Margin':>17}")
    print("-" * 105)

    for var_name, report in ablation_results.items():
        opps = report["opponents"]
        win_pct = report["composite_win_rate"]
        d_v18 = opps["kaitofukami-v18"]["mean_paired_delta"]
        d_v83 = opps["submission_v83"]["mean_paired_delta"]
        d_car = opps["Carrot Rusher"]["mean_paired_delta"]
        d_liv = opps["Livestock Rusher"]["mean_paired_delta"]
        print(f"{var_name:<28} | {win_pct:>11.1%} | ${d_v18:>+11,.2f} | ${d_v83:>+11,.2f} | ${d_car:>+13,.2f} | ${d_liv:>+16,.2f}")

if __name__ == "__main__":
    run_ablation_matrix()
