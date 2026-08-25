"""Experiment 004: Population Tournament Gauntlet across diverse ladder meta archetypes."""
from __future__ import annotations
import sys
import os
import time

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

def run_population_tournament():
    print("=" * 85)
    print("KAGGRICULTURE v1.32.7 POPULATION TOURNAMENT (4 OPPONENT ARCHETYPES)")
    print("=" * 85)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888]
    cand = AdaptiveAgent(enable_forensic_logging=False)
    
    opponents = {
        "1. kaitofukami-v18 (Replay Champion)": bot_v18.agent,
        "2. submission_v83 (APEX Control)": bot_v83.agent,
        "3. Carrot Rusher Bot (44.2% Ladder Meta)": carrot_rusher_agent,
        "4. Livestock Rusher Bot (Cow Maximalist)": livestock_rusher_agent,
    }

    from engine.evaluation.tournament import TournamentEngine
    report = TournamentEngine.run_multi_opponent_gauntlet(cand.act, opponents, test_seeds, steps=720)

    print(f"\n[Population Tournament Complete across {report['total_matches']} full 720-step matches]")
    print(f"Overall Composite Win Rate: {report['composite_win_rate']:.1%}")
    print("-" * 85)

    for opp_name, stats in report["opponents"].items():
        print(f"\n>>> {opp_name}")
        print(f"    - Win Rate: {stats['overall_win_rate']:.1%} ({stats['num_seeds']*2} games)")
        print(f"    - Seat 0 Win Rate: {stats['seat0_win_rate']:.1%}")
        print(f"    - Seat 1 Win Rate: {stats['seat1_win_rate']:.1%}")
        print(f"    - Mean Paired Delta: ${stats['mean_paired_delta']:+,.2f}")
        print(f"    - Total Delta: ${stats['total_delta']:+,.2f}")

if __name__ == "__main__":
    run_population_tournament()
