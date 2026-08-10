"""L+ APEX: Meta Strategy Signature & Market Regime Detector.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from apex.world_model import WorldState, CROPS, ANIMALS

class MetaSignature:
    """Represents the real-time market regime and commodity rankings."""
    def __init__(
        self,
        regime: str,
        commodity_rankings: List[Tuple[str, float]],
        opponent_archetype: str,
        price_volatility: Dict[str, float]
    ):
        self.regime = regime  # "MELON_RUSH", "STRAWBERRY_PASTURE", "LIVESTOCK_WAVE", "BALANCED_HARVEST"
        self.commodity_rankings = commodity_rankings
        self.opponent_archetype = opponent_archetype
        self.price_volatility = price_volatility

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "top_commodity": self.commodity_rankings[0] if self.commodity_rankings else ("NONE", 0.0),
            "commodity_rankings": self.commodity_rankings,
            "opponent_archetype": self.opponent_archetype,
        }

class MetaDetector:
    """Detects market regimes, commodity ROI rankings, and opponent meta shifts."""

    @staticmethod
    def detect_regime(state: WorldState) -> MetaSignature:
        prices = state.prices

        # 1. Compute dynamic ROI per commodity
        commodity_rois = []
        
        # Crops
        for crop, cfg in CROPS.items():
            price = float(prices.get(crop, 20.0))
            seed_cost = cfg["seed"]
            yield_qty = cfg["max_yield"]
            duration_days = cfg["first"]
            
            gross_rev = yield_qty * price
            net_profit = gross_rev - seed_cost
            roi_per_day = (net_profit / max(1, seed_cost)) / max(1, duration_days)
            commodity_rois.append((crop, roi_per_day))

        # Animals / Products
        for animal, cfg in ANIMALS.items():
            product = cfg["product"]
            cost = cfg["cost"]
            price = float(prices.get(product, 160.0))
            daily_rev = price * 0.1
            roi_per_day = (daily_rev * 10.0) / max(1, cost)
            commodity_rois.append((product, roi_per_day))

        # Sort commodities by ROI
        commodity_rois.sort(key=lambda x: x[1], reverse=True)
        top_commodity = commodity_rois[0][0] if commodity_rois else "WHEAT"

        # 2. Detect Opponent Archetype
        opp_tiles = state.opp_tiles
        opp_cows = sum(t.get("animal") == "COW" for t in opp_tiles)
        opp_sheep = sum(t.get("animal") == "SHEEP" for t in opp_tiles)
        opp_melons = sum(t.get("crop") == "MELON" for t in opp_tiles)
        opp_strawberries = sum(t.get("crop") == "STRAWBERRY" for t in opp_tiles)

        if opp_melons >= 6:
            opp_archetype = "MELON_RUSHER"
        elif opp_cows + opp_sheep >= 6:
            opp_archetype = "LIVESTOCK_HEAVY"
        elif opp_strawberries >= 10:
            opp_archetype = "STRAWBERRY_PASTURE"
        else:
            opp_archetype = "BALANCED_COMPETITOR"

        # 3. Classify Market Regime
        melon_price = float(prices.get("MELON", 200.0))
        strawberry_price = float(prices.get("STRAWBERRY", 120.0))
        milk_price = float(prices.get("MILK", 160.0))

        if melon_price >= 200.0 and state.day <= 10 and top_commodity == "MELON":
            regime = "MELON_RUSH"
        elif strawberry_price >= 100.0 and top_commodity in ("STRAWBERRY", "WOOL"):
            regime = "STRAWBERRY_PASTURE"
        elif milk_price >= 160.0 and (opp_cows >= 5 or top_commodity == "MILK"):
            regime = "LIVESTOCK_WAVE"
        else:
            regime = "BALANCED_HARVEST"

        return MetaSignature(
            regime=regime,
            commodity_rankings=commodity_rois,
            opponent_archetype=opp_archetype,
            price_volatility=prices
        )
