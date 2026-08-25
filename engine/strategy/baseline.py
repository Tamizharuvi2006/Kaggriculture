"""High-conviction baseline physical compounding strategy."""
from __future__ import annotations
from typing import Dict, List, Tuple, Any

ANIMAL_SITES = (
    (4, 2), (4, 3), (3, 4), (4, 4),
    (6, 2), (5, 3), (7, 3), (5, 4), (7, 4),
    (3, 5), (4, 5), (3, 6), (4, 6), (4, 7),
)

class BaselineStrategy:
    """Baseline physical compounding configuration and site planner."""

    @staticmethod
    def default_opening_plan() -> Dict[Tuple[int, int], str]:
        """Opening 21-tile allocation for NW quadrant."""
        # 2 Cows at (4,2) and (4,3)
        # 12-15 Melons near the shed for Day 10-12 Land #2/3 funding
        # Wheat for feed buffer & opening liquidity
        plan = {}
        blocked = {(4, 2), (4, 3), (3, 4), (4, 4)}
        slots = [(x, y) for y in range(5) for x in range(5) if (x, y) not in blocked]
        slots.sort(key=lambda p: (abs(p[0] - 4) + abs(p[1] - 4), p[1], p[0]))
        
        for pos in slots[:9]:
            plan[pos] = "MELON"
        for pos in slots[9:11]:
            plan[pos] = "CARROT"
        for pos in slots[11:]:
            plan[pos] = "WHEAT"
        return plan

    @staticmethod
    def default_crop_plan() -> Dict[Tuple[int, int], str]:
        """Full farm target crop plan (Strawberries across NE and SW)."""
        plan = BaselineStrategy.default_opening_plan()
        animal_plan = BaselineStrategy.default_animal_plan()
        candidates = [
            (x, y)
            for y in range(10)
            for x in range(10)
            if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))
            and (x, y) not in animal_plan
            and (x, y) not in plan
        ]
        candidates.sort(key=lambda p: (abs(p[0] - 4.5) + abs(p[1] - 4.5), p[1], p[0]))
        for pos in candidates[:34]:
            plan[pos] = "STRAWBERRY"
        return plan

    @staticmethod
    def default_animal_plan() -> Dict[Tuple[int, int], str]:
        """Animal allocation across the 14 structural animal sites."""
        plan = {}
        for pos in ANIMAL_SITES[:8]:
            plan[pos] = "COW"
        for pos in ANIMAL_SITES[8:14]:
            plan[pos] = "SHEEP"
        return plan
