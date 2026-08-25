"""Track B: MaxMoneyAgent (4-Quadrant 64-Tile High-Capacity Compounding Engine).
Targeting $150,000+ Average Terminal Bank.
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
from engine.macro_money.macro_scheduler import MacroScheduler

class MaxMoneyAgent:
    """Track B High-Capacity Agent: 4 Quadrants, 52 Strawberries, 12 Cows, 18 Workers."""
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

            # 1. Base Physical Spine Actions
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # 2. Track B Expansion: Unlock 4th Quadrant (SE) on Day 15-18 when money >= $3,200
            if n_unlocked == 3 and day >= 15 and farm.money >= 3200.0:
                if not any(len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_LAND"])

            # 3. Track B Labor Expansion: Scale up to 18 workers once 4 quadrants are unlocked
            target_workers = MacroScheduler.get_worker_target(day, n_unlocked)
            if farm.num_workers < target_workers and farm.money >= 1500.0 and day <= 24:
                if not any(len(m) >= 1 and m[0] == "HIRE" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["HIRE"])

            # 4. Track B Strawberry Seed Scaling: Buy extra strawberry seeds for SE quadrant
            if n_unlocked == 4 and 16 <= day <= 22 and farm.money >= 2500.0:
                straw_seeds = farm.seeds.get("STRAWBERRY", 0)
                if straw_seeds < 12 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", 8])

            # 5. Track B Livestock Scaling: Buy 2 extra cows for 2nd pasture once SE is open
            cows_count = len(farm.animals_by_type.get("COW", []))
            if n_unlocked == 4 and cows_count < 12 and 16 <= day <= 20 and farm.money >= 5000.0:
                if not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                    if len(market_orders) < 10:
                        market_orders.append(["BUY_ANIMAL", "COW"])

            # 6. Disciplined Dynamic Selling (Variant D.1 Rule: qty >= 4)
            for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
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

# Kaggle entry point
_GLOBAL_MAX_MONEY = MaxMoneyAgent()

def agent(obs, configuration=None):
    global _GLOBAL_MAX_MONEY
    return _GLOBAL_MAX_MONEY.act(obs, configuration)
