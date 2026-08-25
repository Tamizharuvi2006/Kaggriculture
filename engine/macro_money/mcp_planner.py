"""Track B: Market Capture Planner (MCP) Core Engine.
Calculates real-time Town Demand Holes, Market Scarcity, Shadow Costs,
and Marginal Capture Values to dynamically allocate market order slots.
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import math

class MarketCapturePlanner:
    """Closed-Loop Economic Allocator for Town Market Capture."""
    def __init__(self):
        # Known baseline town shop daily consumption rates (from competition forensics)
        self.base_daily_drain = {
            "WHEAT": 17.5,
            "STRAWBERRY": 14.2,
            "MILK": 10.9,
            "CARROT": 10.9,
            "TOMATO": 7.6,
            "EGG": 7.6,
            "WOOL": 7.6,
            "MELON": 1.0,
            "FERTILIZER": 0.0,
        }
        self.last_prices: Dict[str, float] = {}

    def compute_market_holes(self, obs, market) -> Dict[str, float]:
        """Calculates the remaining town demand hole (units) for each commodity."""
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        remaining_days = max(0.0, (720.0 - step) / 24.0)
        
        holes = {}
        for item, daily_drain in self.base_daily_drain.items():
            current_price = market.price(item)
            base_price = market.base_price(item) if hasattr(market, "base_price") else 100.0
            
            # Scarcity multiplier: price above base indicates town demand is outpacing supply
            scarcity_ratio = max(0.5, current_price / max(1.0, base_price))
            holes[item] = daily_drain * remaining_days * scarcity_ratio
        return holes

    def allocate_market_orders(self, farm, market, obs, base_orders: List[List[Any]]) -> List[List[Any]]:
        """Allocates market order slots based on Marginal Market Capture Value."""
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
        money = farm.money

        # 1. Preserve Essential Operational Orders (BUY_LAND, HIRE, BUY_SEED, BUY_PRODUCT)
        # Also preserve ALL opening bootstrap sell orders (Days 0-6)
        if day <= 6 or step < 150:
            return base_orders[:10]

        operational_orders = [o for o in base_orders if isinstance(o, list) and len(o) > 0 and o[0] != "SELL"]
        
        # 2. Terminal Clearance (Step >= 696)
        if step >= 696:
            clearance_orders = list(operational_orders)
            for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                qty = farm.shed.get(item, 0)
                if qty > 0:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in clearance_orders):
                        if len(clearance_orders) < 10:
                            clearance_orders.append(["SELL", item, qty])
            return clearance_orders[:10]

        # 3. Dynamic Market Capture Allocation (Days 7-28)
        holes = self.compute_market_holes(obs, market)
        sell_candidates: List[Tuple[float, List[Any]]] = []

        # Shadow cost of market order slot ($100 opportunity hurdle)
        slot_shadow_cost = 100.0

        for item, qty in farm.shed.items():
            if qty < 4:
                continue
            p = market.price(item)
            hole = holes.get(item, 0.0)
            
            # Marginal Capture Value = Realized Value * Scarcity Capture Factor - Hurdle
            realized_value = qty * p
            scarcity_capture_factor = 1.2 if hole > qty else 1.0
            marginal_capture = (realized_value * scarcity_capture_factor) - slot_shadow_cost

            # If urgent liquidity needed (cash < $3,000), boost capture value
            if money < 3000.0:
                marginal_capture += 5000.0

            if marginal_capture > 0.0:
                sell_candidates.append((marginal_capture, ["SELL", item, qty]))

        # Sort candidates in descending order of marginal capture value
        sell_candidates.sort(key=lambda x: x[0], reverse=True)

        final_orders = list(operational_orders)
        seen_items = set()
        for _, order in sell_candidates:
            item = order[1]
            if item not in seen_items and len(final_orders) < 10:
                seen_items.add(item)
                final_orders.append(order)

        return final_orders[:10]
