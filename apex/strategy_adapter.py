"""L+ APEX: Strategy Adapter & Dynamic Regime State Switcher.
"""

from __future__ import annotations
from typing import Dict, List, Any
from apex.world_model import WorldState
from apex.meta_model import MetaSignature
from apex.opponent_model import OpponentSignature
from apex.economic_model import CommodityModel

class StrategyState:
    def __init__(self, name: str, focus_commodity: str, target_reserve: float):
        self.name = name
        self.focus_commodity = focus_commodity
        self.target_reserve = target_reserve

class StrategyAdapter:
    """Dynamically adapts strategy regime in-game based on real-time market & opponent signals."""

    @staticmethod
    def select_active_strategy(
        state: WorldState,
        meta: MetaSignature,
        opp: OpponentSignature
    ) -> StrategyState:
        day = state.day
        remaining = state.remaining_steps

        # 1. Terminal Window -> LIQUIDATION
        if remaining <= 48:
            return StrategyState("LIQUIDATION", "ALL", 0.0)

        # 2. Early Game (Days 0-5) -> HEADSTART or MELON_RUSH
        if day <= 5:
            if meta.regime == "MELON_RUSH" or opp.archetype == "AGGRESSIVE_MELON_RUSHER":
                return StrategyState("MELON_RUSH", "MELON", 150.0)
            return StrategyState("HEADSTART", "WHEAT", 150.0)

        # 3. Mid-Game (Days 6-20) -> STRAWBERRY_ENGINE or WOOL_ENGINE
        if day <= 20:
            top_item = meta.commodity_rankings[0][0] if meta.commodity_rankings else "STRAWBERRY"
            if top_item in ("WOOL", "MILK"):
                return StrategyState("LIVESTOCK_ENGINE", top_item, 250.0)
            elif top_item == "MELON":
                return StrategyState("MELON_ENGINE", "MELON", 150.0)
            else:
                return StrategyState("STRAWBERRY_ENGINE", "STRAWBERRY", 200.0)

        # 4. Late Game (Days 21-27) -> BALANCED
        return StrategyState("BALANCED", "ALL", 150.0)
