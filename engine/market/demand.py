"""Town demand and shop consumption trajectory tracker."""
from __future__ import annotations
from typing import Dict, List, Any
from engine.state.market_state import MarketState, SHOPS

class DemandTracker:
    """Tracks active shop demand and future shop unlock probabilities."""
    
    @staticmethod
    def active_shop_demands(market: MarketState) -> Dict[str, float]:
        """Returns per-turn consumption rate for each product across all active shops."""
        rates = {}
        for shop in market.unlocked_shops:
            products = SHOPS.get(shop, [])
            mult = 2.0 if len(products) == 1 else 1.0
            for p in products:
                rates[p] = rates.get(p, 0.0) + (mult / 4.0)
        return rates

    @staticmethod
    def forecast_shop_drain(product: str, market: MarketState, horizons_days: float) -> float:
        """Estimates total units of product town shops will consume over given days."""
        turns = horizons_days * 24.0
        current_rate = market.town_drain_rate(product)
        return current_rate * turns
