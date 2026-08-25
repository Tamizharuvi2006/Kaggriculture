"""Track B (Candidate B.3): Two-Phase Hybrid Dispatcher Engine.
Phase 1 (Steps 0-150): Deterministic opening bootstrap (clearing, hoeing, fencing pasture, initial cows, Land #2).
Phase 2 (Steps 151-720): Dynamic High-Capacity Unit Dispatcher servicing expanded pastures (12 cows) and crop grids.
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
from engine.macro_money.unit_dispatcher import UnitDispatcher

class B3HybridAgent:
    """Candidate B.3: Two-Phase Hybrid Bootstrap + Dynamic Dispatcher."""
    def __init__(self, target_cows: int = 12):
        self.target_cows = target_cows
        self.market_tracker = MarketTracker()

    def reset(self):
        self.market_tracker.reset()

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            obs = Observation(raw_obs, raw_config)
            step = obs.step

            # =========================================================================
            # PHASE 1: DETERMINISTIC OPENING BOOTSTRAP (Steps 0-150 / Days 0-6)
            # =========================================================================
            if step < 150:
                return apex4_mod.agent(raw_obs, raw_config)

            # =========================================================================
            # PHASE 2: DYNAMIC HIGH-CAPACITY DISPATCHER (Steps 151-720 / Days 7-30)
            # =========================================================================
            farm = FarmState(obs)
            market = self.market_tracker.update(obs)
            day = obs.day
            unlocked = farm.unlocked_quadrants
            n_unlocked = len(unlocked)

            market_orders: List[List[Any]] = []

            # 1. Land Expansion Orders (Land #3 on Day 10-14 when cash >= $2,000)
            if n_unlocked == 2 and (day >= 10 or farm.money >= 2000.0) and "SW" not in unlocked:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hiring (Scale to 13 workers)
            if farm.num_workers < 13 and day <= 24 and farm.money >= 500.0:
                market_orders.append(["HIRE"])

            # 3. Expanded Livestock Scaling (Scale up to target_cows)
            cows_count = len(farm.animals_by_type.get("COW", []))
            if cows_count < self.target_cows and n_unlocked >= 3 and 14 <= day <= 20 and farm.money >= 3500.0:
                market_orders.append(["BUY_ANIMAL", "COW"])

            # 4. Disciplined Selling (qty >= 4)
            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    market_orders.append(["SELL", item, qty])

            # 5. Terminal Clearance (Step >= 696)
            if step >= 696:
                for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                    qty = farm.shed.get(item, 0)
                    if qty > 0:
                        market_orders.append(["SELL", item, qty])

            # 6. Dynamic Unit Dispatching for all worker units
            farmer_act, hands_act = UnitDispatcher.dispatch_all(farm)

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders[:10],
            }
        except Exception:
            return apex4_mod.agent(raw_obs, raw_config)

# Singleton entry point
_GLOBAL_B3 = B3HybridAgent(target_cows=12)

def agent(obs, configuration=None):
    global _GLOBAL_B3
    return _GLOBAL_B3.act(obs, configuration)
