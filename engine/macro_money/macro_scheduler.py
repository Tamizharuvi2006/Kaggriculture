"""Track B: High-Capacity Macroeconomic 4-Quadrant Compounding Engine.
Architected to break the $80k ceiling and target $150k+ average terminal wealth:
- 4 Full Quadrants Unlocked (64 tiles: NW, NE, SW, SE)
- 52 Strawberries compounding in synchronized 4x waves
- 12 High-Yield Dairy Cows across 2 optimized 3x2 pastures
- 18 Workers delivering 432 steps/day of physical labor capacity
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, List, Tuple

class MacroScheduler:
    """Manages the 4-quadrant expansion roadmap and tile layout."""

    @staticmethod
    def get_target_quadrants(day: int, money: float, current_unlocked: List[str]) -> List[str]:
        """Calculates optimal land acquisition sequence (NW -> NE -> SW -> SE)."""
        orders = []
        n_unlocked = len(current_unlocked)

        if n_unlocked == 1 and (day >= 6 or money >= 1000.0) and "NE" not in current_unlocked:
            orders.append(["BUY_LAND"])
        elif n_unlocked == 2 and (day >= 10 or money >= 2000.0) and "SW" not in current_unlocked:
            orders.append(["BUY_LAND"])
        elif n_unlocked == 3 and (day >= 15 or money >= 3000.0) and "SE" not in current_unlocked:
            orders.append(["BUY_LAND"])

        return orders

    @staticmethod
    def get_worker_target(day: int, unlocked_count: int) -> int:
        """Determines target labor force capacity for 4-quadrant operations."""
        if unlocked_count == 1:
            return 5
        elif unlocked_count == 2:
            return 9
        elif unlocked_count == 3:
            return 13
        else: # 4 Quadrants unlocked (64 tiles)
            return 18
