"""Strategy Discovery & Daily Ladder Meta Pipeline.
"""

from __future__ import annotations
import os
import glob
from typing import Dict, List, Any
from research.replay_parser import ReplayParser
from research.behavior_extractor import BehaviorExtractor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class StrategyDiscovery:
    """Discovers winning behavior fingerprints across all available local replay logs."""

    @staticmethod
    def analyze_all_replays(replay_dir: str) -> Dict[str, Any]:
        json_files = glob.glob(os.path.join(replay_dir, "*.json"))
        json_files = [f for f in json_files if not f.endswith("-0.json") and not f.endswith("-1.json")]

        winner_counts = []
        loser_counts = []

        for fpath in json_files[:50]:
            parsed = ReplayParser.parse_file(fpath)
            if not parsed:
                continue

            win_idx = parsed["winner_idx"]
            acts_win = parsed["actions_p0"] if win_idx == 0 else parsed["actions_p1"]
            acts_los = parsed["actions_p1"] if win_idx == 0 else parsed["actions_p0"]

            c_win = BehaviorExtractor.extract_counts(acts_win)
            c_los = BehaviorExtractor.extract_counts(acts_los)

            winner_counts.append(c_win)
            loser_counts.append(c_los)

        avg_win = {k: sum(c[k] for c in winner_counts) / max(1, len(winner_counts)) for k in c_win} if winner_counts else {}
        avg_los = {k: sum(c[k] for c in loser_counts) / max(1, len(loser_counts)) for k in c_los} if loser_counts else {}

        return {
            "replays_analyzed": len(winner_counts),
            "winner_avg_action_counts": avg_win,
            "loser_avg_action_counts": avg_los,
        }

if __name__ == "__main__":
    res = StrategyDiscovery.analyze_all_replays(os.path.join(BASE_DIR, "l+reviews", "newl"))
    print("Strategy Discovery Analysis Summary:")
    print(res)
