"""Valuation of scarce market order slots (10-order cap)."""
from __future__ import annotations
from typing import List, Any

MAX_MARKET_ORDERS = 10

class MarketSlotValuator:
    """Prioritizes and budgets market orders under the strict 10-order limit."""

    @staticmethod
    def prioritize_orders(orders: List[List[Any]], current_cash: float, safe_buffer: float) -> List[List[Any]]:
        """Orders are sorted by economic criticality:
        1. Essential Land / Feed solvency orders
        2. High-value liquidity cash conversion (SELL high value)
        3. Critical labor hires
        4. High-ROI seed purchases
        5. Secondary sales
        """
        if len(orders) <= MAX_MARKET_ORDERS:
            return orders

        def order_rank(ord_item: List[Any]) -> float:
            if not ord_item:
                return 999.0
            op = ord_item[0]
            if op == "BUY_LAND":
                return 0.0  # Land unlock is top milestone
            if op == "BUY_PRODUCT" and len(ord_item) > 1 and ord_item[1] == "WHEAT":
                return 1.0  # Feed is existential
            if op == "SELL":
                item = ord_item[1] if len(ord_item) > 1 else ""
                if current_cash < safe_buffer:
                    return 2.0  # Cash conversion is critical when constrained
                if item in ("MELON", "STRAWBERRY", "TOMATO", "MILK"):
                    return 3.0
                return 5.0
            if op == "HIRE":
                return 4.0
            if op == "BUY_SEED":
                return 6.0
            return 10.0

        sorted_orders = sorted(orders, key=order_rank)
        return sorted_orders[:MAX_MARKET_ORDERS]
