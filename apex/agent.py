"""L+ APEX: Monolithic Kaggle-Compatible Autonomous Agent Entry Point.
"""

from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from apex.world_model import WorldState
from apex.policy import ApexPolicy
from apex.memory import MemorySystem

_POLICY = ApexPolicy(mode="advisor_guided")
_MEMORY = MemorySystem()

def agent(obs, config=None):
    """Kaggle environment entry point for L+ APEX."""
    try:
        state = WorldState(obs)
        action = _POLICY.select_action(obs, state)
        _MEMORY.record_turn({"step": state.step, "day": state.day, "money": state.money}, action)
        return action
    except Exception as e:
        # Fallback to expert baseline directly if error occurs
        from generalization_pipeline.submission_candidate_l_plus import _v18_closed_loop_action
        step = obs.get("step", 0) if isinstance(obs, dict) else 0
        return _v18_closed_loop_action(obs, step)
