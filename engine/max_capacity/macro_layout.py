"""Track B: High-Capacity Macro Layout Engine.
Optimizes 4-Quadrant land allocation across Livestock Pastures, Strawberries, and Fast-Turnaround Melons:
- Quadrant 1 (NW): Farmhouse, Shed, 6-Cow Primary Pasture
- Quadrant 2 (NE): 16-Strawberry High-Yield Compounding Grid
- Quadrant 3 (SW): 6-Cow Secondary Pasture + 8 Fast-Cycle Melons
- Quadrant 4 (SE): 6-Cow Tertiary Pasture + 8 Fast-Cycle Melons
Total Capacity: 18 Cows + 16 Strawberries + 16 Fast Melons = 50 Productive Tiles.
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple

class MacroLayoutPlanner:
    """Calculates optimal land, livestock, and crop assignments across 64 tiles."""

    @staticmethod
    def get_land_purchase_orders(day: int, money: float, unlocked: List[str]) -> List[List[str]]:
        """Precision land unlocking sequence."""
        orders = []
        n = len(unlocked)
        if n == 1 and (day >= 6 or money >= 1000.0) and "NE" not in unlocked:
            orders.append(["BUY_LAND"])
        elif n == 2 and (day >= 10 or money >= 2000.0) and "SW" not in unlocked:
            orders.append(["BUY_LAND"])
        elif n == 3 and (day >= 14 or money >= 3000.0) and "SE" not in unlocked:
            orders.append(["BUY_LAND"])
        return orders

    @staticmethod
    def get_livestock_targets(unlocked_count: int) -> int:
        """Scales cows proportionally with unlocked pasture space."""
        if unlocked_count == 1:
            return 4
        elif unlocked_count == 2:
            return 8
        elif unlocked_count == 3:
            return 12
        else: # 4 Quadrants
            return 16
