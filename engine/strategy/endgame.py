"""Endgame liquidation and clearance execution engine."""
from __future__ import annotations
from typing import List, Any
from engine.state.farm_state import FarmState
from engine.state.observation import SELLABLE

class EndgameClearanceEngine:
    """Handles terminal liquidation and avoids deadweight inventory loss."""

    @staticmethod
    def generate_clearance_orders(farm: FarmState, step: int) -> List[List[Any]]:
        """Force sells all products in the shed at step >= 700."""
        if step < 700:
            return []

        orders = []
        for item in SELLABLE:
            qty = farm.shed.get(item, 0)
            if qty > 0:
                orders.append(["SELL", item, qty])
        
        # On final day, also sell any remaining wheat
        wheat_qty = farm.shed.get("WHEAT", 0)
        if step >= 696 and wheat_qty > 0:
            orders.append(["SELL", "WHEAT", wheat_qty])

        return orders
