"""Track B (Candidate B.2): Custom Tile Action Dispatcher Agent.
Uses dynamic unit dispatching to physically service expanded pastures and crop grids.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketTracker
from engine.macro_money.unit_dispatcher import UnitDispatcher

class B2DispatchAgent:
    """Candidate B.2: Dynamic Tile Dispatcher with Scalable Pastures."""
    def __init__(self, target_cows: int = 12):
        self.target_cows = target_cows
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

            market_orders: List[List[Any]] = []

            # 1. Land Expansion Orders
            if n_unlocked == 1 and (day >= 6 or farm.money >= 1000.0) and "NE" not in unlocked:
                market_orders.append(["BUY_LAND"])
            elif n_unlocked == 2 and (day >= 10 or farm.money >= 2000.0) and "SW" not in unlocked:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hiring (Scale to 13 workers)
            if farm.num_workers < 13 and day <= 24 and farm.money >= 500.0:
                market_orders.append(["HIRE"])

            # 3. Livestock Scaling (Scale up to target_cows)
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

            # 6. Dynamic Unit Dispatching
            farmer_act, hands_act = UnitDispatcher.dispatch_all(farm)

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders[:10],
            }
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}

# Singleton entry point
_GLOBAL_B2 = B2DispatchAgent(target_cows=12)

def agent(obs, configuration=None):
    global _GLOBAL_B2
    return _GLOBAL_B2.act(obs, configuration)
