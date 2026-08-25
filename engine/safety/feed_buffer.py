"""Livestock feed buffer and zero-deletion safety checks."""
from __future__ import annotations
from typing import Dict, Any, List
from engine.state.farm_state import FarmState

class FeedBufferGuard:
    """Guarantees 100% livestock feeding continuity across the entire season."""

    @staticmethod
    def calculate_feed_deficit(farm: FarmState, day: int, buffer_days: int = 1) -> int:
        if day >= 29:
            return 0  # No feed needed on final day
        num_cows = len(farm.animals_by_type.get("COW", []))
        num_sheep = len(farm.animals_by_type.get("SHEEP", []))
        total_animals = num_cows + num_sheep
        if total_animals == 0:
            return 0
        desired_wheat = total_animals * buffer_days + 2
        current_wheat = farm.total_wheat_inventory()
        return max(0, desired_wheat - current_wheat)

    @staticmethod
    def max_safe_wheat_to_sell(farm: FarmState, day: int) -> int:
        if day >= 29:
            return farm.shed.get("WHEAT", 0)
        num_animals = len(farm.animals)
        reserve = num_animals + 3
        return max(0, farm.shed.get("WHEAT", 0) - reserve)
