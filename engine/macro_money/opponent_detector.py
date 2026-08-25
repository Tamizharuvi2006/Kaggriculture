"""Track B (Candidate EXP036): Opponent Dependency Detector & Asymmetric Market Pressure Engine.
Preserves 100% of D.1 physical execution, liquidity speed, and bootstrap.
Classifies opponent archetype from public farm observation and strategically prioritizes
market order slots to preempt the opponent's primary revenue commodity.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional

class OpponentDependencyDetector:
    """Classifies opponent archetype and outputs optimal commodity sale priority."""
    def __init__(self):
        self.archetype = "BALANCED"

    def classify_opponent(self, obs) -> str:
        """Classifies opponent from public map state."""
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        opp_idx = 1 - player
        if len(farms) <= opp_idx:
            return "BALANCED"

        opp_farm = farms[opp_idx]
        tiles = opp_farm.get("tiles") or []
        
        cows = 0
        sheep = 0
        crops = 0
        
        for row in tiles:
            for tile in row:
                if not tile or not isinstance(tile, dict):
                    continue
                kind = tile.get("kind")
                if kind == "PASTURE":
                    animal = tile.get("animal")
                    if animal == "COW":
                        cows += 1
                    elif animal == "SHEEP":
                        sheep += 1
                elif kind == "PLANT":
                    crops += 1

        total_animals = cows + sheep
        if total_animals >= 6 and crops <= 20:
            self.archetype = "LIVESTOCK_DEPENDENT"
        elif crops >= 28 and total_animals <= 4:
            self.archetype = "CROP_DEPENDENT"
        else:
            self.archetype = "BALANCED"
        return self.archetype

    def prioritize_orders(self, farm, market, obs, base_orders: List[List[Any]]) -> List[List[Any]]:
        """Orders market sales to exert asymmetric price pressure on the opponent."""
        step = int(obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0) or 0)
        day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)

        # 1. Preserve Essential Operational Orders & Opening Bootstrap (Days 0-6)
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

        # 3. Opponent Archetype Classification
        archetype = self.classify_opponent(obs)

        # Determine priority ordering based on opponent dependency
        if archetype == "LIVESTOCK_DEPENDENT":
            # Opponent relies on Milk -> Prioritize Milk sales at position #0
            priority_list = ("MILK", "STRAWBERRY", "WOOL", "TOMATO", "CARROT", "MELON")
        elif archetype == "CROP_DEPENDENT":
            # Opponent relies on Crops -> Prioritize Strawberry sales at position #0
            priority_list = ("STRAWBERRY", "MILK", "WOOL", "TOMATO", "CARROT", "MELON")
        else:
            # Balanced -> Standard highest liquidity value
            priority_list = ("STRAWBERRY", "MILK", "WOOL", "TOMATO", "CARROT", "MELON")

        sell_orders: List[List[Any]] = []
        for item in priority_list:
            qty = farm.shed.get(item, 0)
            if qty >= 4:
                sell_orders.append(["SELL", item, qty])

        final_orders = list(operational_orders)
        seen_items = set()
        for order in sell_orders:
            item = order[1]
            if item not in seen_items and len(final_orders) < 10:
                seen_items.add(item)
                final_orders.append(order)

        return final_orders[:10]
