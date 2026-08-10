"""L+ APEX: Real-Time Opponent Signature & Behavior Model.
"""

from __future__ import annotations
from typing import Dict, Any
from apex.world_model import WorldState

class OpponentSignature:
    def __init__(self, archetype: str, aggressiveness: float, expansion_rate: float):
        self.archetype = archetype  # "AGGRESSIVE_MELON_RUSHER", "DEFENSIVE_LIVESTOCK", "STRAWBERRY_PASTURE", "BALANCED"
        self.aggressiveness = aggressiveness
        self.expansion_rate = expansion_rate

class OpponentModel:
    """Tracks opponent public state to classify real-time competitor behavior."""

    @staticmethod
    def analyze_opponent(state: WorldState) -> OpponentSignature:
        opp_tiles = getattr(state, "opp_tiles", [])
        opp_unlocked_quads = getattr(state, "opp_unlocked_quadrants", getattr(state, "opp_unlocked", []))
        opp_unlocked = len(opp_unlocked_quads)
        
        melons = sum(t.get("crop") == "MELON" for t in opp_tiles)
        cows = sum(t.get("animal") == "COW" for t in opp_tiles)
        sheep = sum(t.get("animal") == "SHEEP" for t in opp_tiles)
        strawberries = sum(t.get("crop") == "STRAWBERRY" for t in opp_tiles)

        aggressiveness = 0.5
        if opp_unlocked >= 2 and state.day <= 5:
            aggressiveness = 0.9

        if melons >= 6:
            archetype = "AGGRESSIVE_MELON_RUSHER"
        elif cows + sheep >= 5:
            archetype = "DEFENSIVE_LIVESTOCK"
        elif strawberries >= 8:
            archetype = "STRAWBERRY_PASTURE"
        else:
            archetype = "BALANCED"

        return OpponentSignature(
            archetype=archetype,
            aggressiveness=aggressiveness,
            expansion_rate=float(opp_unlocked) / max(1, state.day)
        )
