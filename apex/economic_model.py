"""L+ APEX: Commodity-Agnostic Dynamic Economic Model.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState, CROPS, ANIMALS

class CommodityMetrics:
    """Standardized metrics for any commodity in the game."""
    def __init__(
        self,
        name: str,
        category: str,
        cost: float,
        cycle_steps: int,
        expected_yield: float,
        unit_price: float,
        net_profit: float,
        roi_per_step: float,
        terminal_liquidation_value: float
    ):
        self.name = name
        self.category = category
        self.cost = cost
        self.cycle_steps = cycle_steps
        self.expected_yield = expected_yield
        self.unit_price = unit_price
        self.net_profit = net_profit
        self.roi_per_step = roi_per_step
        self.terminal_liquidation_value = terminal_liquidation_value

class CommodityModel:
    """Commodity-agnostic valuation engine for all crops, livestock, and items."""

    @staticmethod
    def evaluate_commodity(name: str, state: WorldState) -> CommodityMetrics:
        prices = state.prices
        price = float(prices.get(name, 10.0))

        if name in CROPS:
            cfg = CROPS[name]
            cost = float(cfg["seed"])
            cycle_steps = cfg["first"] * 24
            yield_qty = float(cfg["max_yield"])
            gross_rev = yield_qty * price
            net_profit = gross_rev - cost
            roi_per_step = (net_profit / max(1.0, cost)) / max(1, cycle_steps)
            term_val = yield_qty * price if state.remaining_steps >= cycle_steps else 0.0
            
            return CommodityMetrics(
                name=name,
                category="CROP",
                cost=cost,
                cycle_steps=cycle_steps,
                expected_yield=yield_qty,
                unit_price=price,
                net_profit=net_profit,
                roi_per_step=roi_per_step,
                terminal_liquidation_value=term_val
            )

        elif name in ("MILK", "WOOL", "EGG"):
            animal = "COW" if name == "MILK" else "SHEEP"
            cost = float(ANIMALS.get(animal, {}).get("cost", 400.0))
            cycle_steps = 24
            yield_qty = 1.0
            gross_rev = price
            net_profit = gross_rev
            roi_per_step = (gross_rev / max(1.0, cost)) / max(1, cycle_steps)
            
            return CommodityMetrics(
                name=name,
                category="ANIMAL_PRODUCT",
                cost=cost,
                cycle_steps=cycle_steps,
                expected_yield=yield_qty,
                unit_price=price,
                net_profit=net_profit,
                roi_per_step=roi_per_step,
                terminal_liquidation_value=price
            )

        else:
            return CommodityMetrics(
                name=name,
                category="INPUT",
                cost=10.0,
                cycle_steps=1,
                expected_yield=1.0,
                unit_price=price,
                net_profit=0.0,
                roi_per_step=0.0,
                terminal_liquidation_value=price
            )

    @staticmethod
    def rank_all_commodities(state: WorldState) -> List[CommodityMetrics]:
        all_items = list(CROPS.keys()) + ["MILK", "WOOL", "FERTILIZER"]
        metrics_list = [CommodityModel.evaluate_commodity(item, state) for item in all_items]
        metrics_list.sort(key=lambda m: m.roi_per_step, reverse=True)
        return metrics_list

    @staticmethod
    def total_farm_liquidation_value(state: WorldState) -> float:
        total = state.money
        for item, qty in state.inventory.items():
            price = float(state.prices.get(item, 10.0))
            total += qty * price
        return total

class EconomicModel:
    """Legacy interface compatibility wrapper around CommodityModel."""
    @staticmethod
    def crop_roi(crop_name: str, state: WorldState) -> float:
        return CommodityModel.evaluate_commodity(crop_name, state).roi_per_step

    @staticmethod
    def animal_roi(animal_name: str, state: WorldState) -> float:
        product = ANIMALS.get(animal_name, {}).get("product", "MILK")
        return CommodityModel.evaluate_commodity(product, state).roi_per_step
