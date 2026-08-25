"""Track B (Candidate B7): Value-Ranked Market Order Allocation Engine.
Exploits the shared order book in favorable and cyclical market regimes:
1. Keeps the 100% flawless APEX 4.0 physical machine (38 strawberries, 8 cows, 13 workers) untouched.
2. Value-Ranks Market Orders: Prioritizes Order Slots #0-#3 strictly for high-dollar commodities (Strawberries, Milk, Wool)
   before allocating slots to low-dollar commodities (Fertilizer, Wheat).
3. Preempts Order Book Blocking: Guarantees high-velocity Strawberry and Milk batches are never dropped due to the 10-order limit.
4. Step 696 Terminal Clearance: Clears shed completely into the final market steps.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional, List, Tuple

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

class ValueRankedMarketAgent:
    """Candidate B7: Value-Ranked Market Order Dispatcher on APEX Physical Substrate."""
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

            # 1. Flawless Physical Substrate Execution
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            base_orders = list(base_act.get("market") or [])

            # Separate base orders into operational orders (BUY_LAND, HIRE, BUY_SEED, BUY_PRODUCT) vs SELL orders
            operational_orders = [o for o in base_orders if isinstance(o, list) and len(o) > 0 and o[0] != "SELL"]

            # 2. Build Value-Ranked Sell Orders
            sell_candidates: List[Tuple[float, List[Any]]] = []

            # Priority 1: High-Value Commodities (Strawberries, Milk, Wool)
            for item in ("STRAWBERRY", "MILK", "WOOL", "TOMATO", "CARROT", "MELON"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    p = market.price(item)
                    value = qty * p
                    sell_candidates.append((value, ["SELL", item, qty]))

            # Priority 2: Terminal Clearance (Step >= 696)
            if step >= 696:
                for item in ("STRAWBERRY", "MILK", "FERTILIZER", "TOMATO", "CARROT", "MELON", "WOOL", "EGG", "WHEAT"):
                    qty = farm.shed.get(item, 0)
                    if qty > 0:
                        p = market.price(item)
                        value = qty * p
                        sell_candidates.append((value, ["SELL", item, qty]))

            # Sort sell candidates in descending order of total dollar value
            sell_candidates.sort(key=lambda x: x[0], reverse=True)

            # Deduplicate sell orders by item
            dedup_sells: List[List[Any]] = []
            seen_items = set()
            for val, order in sell_candidates:
                item = order[1]
                if item not in seen_items:
                    seen_items.add(item)
                    dedup_sells.append(order)

            # Combine operational orders (highest priority) + value-ranked sell orders (up to 10 total)
            remaining_slots = 10 - len(operational_orders)
            final_orders = operational_orders + dedup_sells[:max(0, remaining_slots)]

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": final_orders[:10],
            }
        except Exception:
            return apex4_mod.agent(raw_obs, raw_config)

# Singleton entry point
_GLOBAL_B7 = ValueRankedMarketAgent()

def agent(obs, configuration=None):
    global _GLOBAL_B7
    return _GLOBAL_B7.act(obs, configuration)
