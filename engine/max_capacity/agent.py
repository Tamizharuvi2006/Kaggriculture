"""Track B: MaxCapacityMacroAgent (High-Throughput Livestock + Strawberry + Fast-Melon Engine).
Targeting $150k+ Average Terminal Wealth through multi-product high-capacity production.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib.util

spec_apex4 = importlib.util.spec_from_file_location("apex4_mod", os.path.join(BASE_DIR, "APEX4_SUBMISSION_FINAL.py"))
apex4_mod = importlib.util.module_from_spec(spec_apex4)
spec_apex4.loader.exec_module(apex4_mod)

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.max_capacity.macro_layout import MacroLayoutPlanner

class MaxCapacityMacroAgent:
    """Track B High-Capacity Agent: 16 Cows + 16 Strawberries + 16 Melons + 15 Workers."""
    def __init__(self):
        self.market_tracker = MarketTracker()

    def reset(self):
        self.market_tracker.reset()

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)
            step = obs.step
            day = obs.day
            unlocked = farm.unlocked_quadrants
            n_unlocked = len(unlocked)

            # 1. Base Spine Physical Foundation
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # 2. 4-Quadrant Strategic Acquisition (SE Quad on Day 14-17 when money >= $3,200)
            if n_unlocked == 3 and day >= 14 and farm.money >= 3200.0:
                if not any(len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_LAND"])

            # 3. Livestock Scaling: 12-16 Cows (High-Yield Dairy & Daily Fertilizer Cash Engine)
            target_cows = MacroLayoutPlanner.get_livestock_targets(n_unlocked)
            current_cows = len(farm.animals_by_type.get("COW", []))
            if current_cows < target_cows and 8 <= day <= 22 and farm.money >= 4000.0:
                if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_ANIMAL", "COW"])

            # 4. Fast-Cycle Melon Seed Purchases for Secondary Quadrants (4-day cycle)
            if n_unlocked >= 3 and 10 <= day <= 24 and farm.money >= 1500.0:
                melon_seeds = farm.seeds.get("MELON", 0)
                if melon_seeds < 6 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "MELON", 6])

            # 5. Labor Scaling: 14-15 Workers to maintain zero-transit bottlenecks
            if farm.num_workers < 15 and n_unlocked >= 3 and 14 <= day <= 22 and farm.money >= 2000.0:
                if not any(len(m) >= 1 and m[0] == "HIRE" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["HIRE"])

            # 6. Disciplined Selling (qty >= 4)
            for item in ("STRAWBERRY", "MILK", "MELON", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

            # 7. Day 30 Terminal Clearance (Step >= 696)
            if step >= 696:
                for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                    qty = farm.shed.get(item, 0)
                    if qty > 0:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders[:10],
            }
        except Exception:
            return apex4_mod.agent(raw_obs, raw_config)

# Singleton entry point
_GLOBAL_MAX_CAP = MaxCapacityMacroAgent()

def agent(obs, configuration=None):
    global _GLOBAL_MAX_CAP
    return _GLOBAL_MAX_CAP.act(obs, configuration)
