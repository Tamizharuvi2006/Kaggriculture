"""Replay Parser & Data Extraction Tool for Kaggriculture Research Pipeline.
"""

from __future__ import annotations
import json
import os
import glob
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ReplayParser:
    """Parses replay JSON logs into structured 720-step action trajectories."""

    @staticmethod
    def parse_file(fpath: str) -> Dict[str, Any]:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = data.get("steps", [])
        if not steps:
            return {}

        last = steps[-1]
        p0 = float(last[0]["observation"]["farms"][0]["money"])
        p1 = float(last[1]["observation"]["farms"][1]["money"])
        
        winner_idx = 0 if p0 >= p1 else 1

        actions_p0 = []
        actions_p1 = []

        for step in steps:
            act0 = step[0].get("action", {})
            act1 = step[1].get("action", {})
            actions_p0.append(act0)
            actions_p1.append(act1)

        return {
            "file": os.path.basename(fpath),
            "p0_wealth": p0,
            "p1_wealth": p1,
            "winner_idx": winner_idx,
            "margin": abs(p0 - p1),
            "total_steps": len(steps),
            "actions_p0": actions_p0,
            "actions_p1": actions_p1,
        }
