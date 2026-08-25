"""Experiment 003: Paired Tournament Gauntlet with Seat-Swapping and Forensic Logs."""
from __future__ import annotations
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

# 1. Load Candidate Agent from engine
from engine.agent import AdaptiveAgent

# 2. Load Baseline Bots
spec_v18 = importlib.util.spec_from_file_location("bot_v18", os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py"))
bot_v18 = importlib.util.module_from_spec(spec_v18)
spec_v18.loader.exec_module(bot_v18)

spec_v83 = importlib.util.spec_from_file_location("bot_v83", os.path.join(BASE_DIR, "baseline", "submission_v83_standalone.py"))
bot_v83 = importlib.util.module_from_spec(spec_v83)
spec_v83.loader.exec_module(bot_v83)

def run_tournament():
    print("=" * 85)
    print("KAGGRICULTURE v1.32.7 EMPIRICAL TOURNAMENT GAUNTLET (SEAT-SWAP PAIRED)")
    print("=" * 85)

    test_seeds = [42, 100, 2026, 590244349, 999999, 12345, 777777, 888888]
    
    cand = AdaptiveAgent(enable_forensic_logging=True)
    
    def candidate_fn(obs, config=None):
        return cand.act(obs, config)

    opponents = {
        "kaitofukami-v18 (Replay Champion)": bot_v18.agent,
        "submission_v83 (APEX Control)": bot_v83.agent,
    }

    start_time = time.time()

    from engine.evaluation.tournament import TournamentEngine
    report = TournamentEngine.run_multi_opponent_gauntlet(candidate_fn, opponents, test_seeds, steps=720)
    
    elapsed = time.time() - start_time

    print(f"\n[Tournament Complete in {elapsed:.1f}s across {report['total_matches']} full 720-step matches]")
    print(f"Overall Composite Win Rate: {report['composite_win_rate']:.1%}")
    print("-" * 85)
    
    for opp_name, stats in report["opponents"].items():
        print(f"\n>>> Opponent: {opp_name}")
        print(f"    - Win Rate: {stats['overall_win_rate']:.1%} ({stats['num_seeds']*2} games)")
        print(f"    - Seat 0 (First Move) Win Rate : {stats['seat0_win_rate']:.1%}")
        print(f"    - Seat 1 (Second Move) Win Rate: {stats['seat1_win_rate']:.1%}")
        print(f"    - Mean Paired Delta: ${stats['mean_paired_delta']:+,.2f}")
        print(f"    - Total Delta: ${stats['total_delta']:+,.2f}")

    # Export forensic logs from last match
    os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)
    log_path = os.path.join(BASE_DIR, "reports", "EXP001_FORENSIC_DECISIONS.jsonl")
    cand.forensic_logger.export_jsonl(log_path)
    cand.forensic_logger.export_summary_md(os.path.join(BASE_DIR, "reports", "EXP001_FORENSIC_SUMMARY.md"))
    print(f"\nForensic decision trace exported to: {log_path}")

if __name__ == "__main__":
    run_tournament()
