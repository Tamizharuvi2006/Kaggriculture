"""Track B (Iteration 2): Dense 3-Quadrant Multi-Product Engine (Dense3QuadAgent).
Eliminates the $3,000 Land #4 cost barrier by packing:
- 12 High-Yield Dairy Cows (Dual 3x2 Pastures in NW and SW)
- 38 Synchronized Strawberries (NE and SW grids)
- 4 Fast-Turnaround Melons (4-day liquidity cycle in SW perimeter)
- 14 Dedicated Workers (Zero-Transit Labor Allocation)
Targeting $100k-$120k+ Average Terminal Bank with positive win rates.
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

class Dense3QuadAgent:
    """Track B High-Density Agent: 12 Cows + 38 Strawberries + 4 Fast Melons in 3 Quadrants."""
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

            # 2. Dense Livestock Scaling (Scale from 8 to 12 cows on Days 14-20 when cash >= $3,500)
            cows_count = len(farm.animals_by_type.get("COW", []))
            if cows_count < 12 and n_unlocked >= 3 and 14 <= day <= 20 and farm.money >= 3500.0:
                if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_ANIMAL", "COW"])

            # 3. Fast Melon Injections on Days 12-22 (4-day harvest turnaround)
            if n_unlocked >= 3 and 12 <= day <= 20 and farm.money >= 1200.0:
                melon_seeds = farm.seeds.get("MELON", 0)
                if melon_seeds < 4 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "MELON", 4])

            # 4. Disciplined Selling (qty >= 4)
            for item in ("STRAWBERRY", "MILK", "MELON", "TOMATO", "CARROT", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

            # 5. Day 30 Terminal Clearance (Step >= 696)
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
_GLOBAL_DENSE_3Q = Dense3QuadAgent()

def agent(obs, configuration=None):
    global _GLOBAL_DENSE_3Q
    return _GLOBAL_DENSE_3Q.act(obs, configuration)
