"""L+ APEX: Expert Knowledge Source (Phase 1 & Phase 3 Integration).
Ensures accurate step propagation to L+ expert schedule lookup.
"""

from __future__ import annotations
import os
import sys
import importlib.util
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LPLUS_PATH = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")

class LPlusExpert:
    """Interface to query L+ 4.1's expert decision policy."""

    def __init__(self, script_path: str = LPLUS_PATH):
        self.script_path = script_path
        self.agent_fn = self._load_agent()

    def _load_agent(self):
        spec = importlib.util.spec_from_file_location("lplus_expert_mod", self.script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent

    def decide(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Queries L+ 4.1 for its exact action recommendation given an observation."""
        try:
            day = int(obs.get("day", 0))
            hour = int(obs.get("hour", 0))
            step = int(obs.get("step", day * 24 + hour))

            obs_copy = dict(obs)
            obs_copy["step"] = step
            return self.agent_fn(obs_copy)
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}
