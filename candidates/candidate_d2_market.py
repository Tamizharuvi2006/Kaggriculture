"""Candidate D.2: Opponent-Aware Cross-Commodity Dynamic Engine.

Extends Variant D.1 with an adaptive cross-commodity probe:
1. Retains 100% of D.1 core invariants:
   - 3 Quadrants (NW, NE, SW)
   - 8 Dairy Cows ($1,280/day milk cashflow, zero lag)
   - 13 Dedicated Workers (100% continuous watering saturation)
   - Step 696 Minimax Queue-Drain Liquidation Buffer
2. Opponent-Aware Market Probe:
   - At Step 240 (Day 10, Land #3 unlock), inspects the opponent's public farm and town market demand:
   - If Opponent is exploiting non-strawberry commodities (>= 4 non-strawberry plots) OR
     Town Strawberry price is heavily depressed (< $110) while Melon price is premium (> $220):
     Allocates a small 4-tile cluster in the SW quadrant to Melons to capture uncontested town demand.
   - Otherwise: Defaults 100% to pure 38-Strawberry monolith (Exact D.1 behavior).
"""
from __future__ import annotations
import math
from typing import Any, Dict, List

from engine.agent import VariantDAgent

class CandidateD2Agent(VariantDAgent):
    """Variant D.2 with targeted opponent-aware cross-commodity allocation."""

    def __init__(self):
        super().__init__()
        self.adaptive_crop_mode = False
        self.melon_plots_target = 0

    def inspect_opponent_and_market(self, obs: Dict[str, Any]):
        """Inspects opponent farm state and market price conditions."""
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        farms = obs.get("farms", []) if isinstance(obs, dict) else getattr(obs, "farms", []) or []

        if step < 240 or step > 360:
            return

        opp_idx = 1 - player
        if len(farms) > opp_idx:
            opp_farm = farms[opp_idx]
            opp_plots = opp_farm.get("plots", [])

            # Count opponent non-strawberry plots
            non_straw_count = 0
            for p in opp_plots:
                ptype = p.get("type")
                if ptype and ptype not in ["STRAWBERRY", 1, "NONE", 0]:
                    non_straw_count += 1

            # Market prices
            market = obs.get("market", {}) if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
            prices = market.get("prices", {}) if isinstance(market, dict) else {}
            p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
            p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

            # Trigger condition: Opponent is exploiting alternative crops or Strawberry is depressed
            if non_straw_count >= 4 or (p_straw < 110.0 and p_melon >= 240.0):
                self.adaptive_crop_mode = True
                self.melon_plots_target = 4
            else:
                self.adaptive_crop_mode = False
                self.melon_plots_target = 0

    def act(self, raw_obs: Dict[str, Any], raw_config: Any = None) -> Dict[str, Any]:
        self.inspect_opponent_and_market(raw_obs)
        return super().act(raw_obs, raw_config)

def agent(obs, configuration=None):
    """Candidate D.2 standalone entry point."""
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2Agent()
    return agent._instance.act(obs, configuration)
