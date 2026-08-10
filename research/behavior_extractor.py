"""Behavior Extractor & Fingerprint Aggregator for Replays.
"""

from __future__ import annotations
import os
import glob
from typing import Dict, List, Any
from research.replay_parser import ReplayParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class BehaviorExtractor:
    """Extracts aggregate action counts and fingerprints from parsed replay trajectories."""

    @staticmethod
    def extract_counts(actions_list: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {
            "SELL": 0,
            "HIRE": 0,
            "BUY_SEED": 0,
            "BUY_ANIMAL": 0,
            "BUY_LAND": 0,
            "HARVEST": 0,
            "FERTILIZER": 0
        }

        for act in actions_list:
            if not isinstance(act, dict):
                continue
            market = act.get("market", [])
            for ord in market:
                if isinstance(ord, list) and len(ord) >= 1:
                    cmd = ord[0]
                    if cmd in counts:
                        counts[cmd] += 1

            hands = act.get("hands", [])
            for h in hands:
                if isinstance(h, list) and len(h) >= 1:
                    cmd = h[0]
                    if cmd in ("HARVEST", "COLLECT_FERTILIZER"):
                        key = "HARVEST" if cmd == "HARVEST" else "FERTILIZER"
                        counts[key] += 1

        return counts
