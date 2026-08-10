"""L+ APEX: Time & Transit Budget Engine.
"""

from __future__ import annotations
import math
from typing import Tuple, Dict, Any
from apex.world_model import WorldState

class TimeModel:
    """Evaluates turn budget constraints, action transit costs, and terminal deadlines."""

    @staticmethod
    def distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    @staticmethod
    def action_can_complete(state: WorldState, transit_steps: int, task_steps: int) -> bool:
        required = transit_steps + task_steps
        return state.remaining_steps >= required

    @staticmethod
    def is_terminal_window(state: WorldState, window_steps: int = 48) -> bool:
        return state.remaining_steps <= window_steps

    @staticmethod
    def time_discount_factor(state: WorldState) -> float:
        """Returns a discount factor from 1.0 (early game) to 0.0 (final turn)."""
        return max(0.0, state.remaining_steps / float(state.total_steps))
