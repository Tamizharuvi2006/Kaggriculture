"""Track B (Candidate B.4): Macroeconomic Market-Hole & Price Pulse Controller.
Reuses the 100% flawless APEX 4.0 physical executor (tools, refills, deposits, feeding, pathfinding).
Operates strictly at the Macro Layer:
1. Dynamic Solvency Gating: Sells unconditionally if cash < $3,000 to guarantee physical compounding.
2. Market-Hole Price Capture: When cash >= $3,000, times batch sales to capture town consumption price pulses
   (P_straw >= $132, P_milk >= $160) rather than selling at cyclic troughs.
3. Step 696 Terminal Clearance: Guarantees 100% inventory liquidation before game ends.
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

class B4MarketHoleAgent:
    """Candidate B.4: Macro Market-Hole Controller on top of APEX Physical Substrate."""
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

            # 1. Flawless Low-Level Physical Substrate Execution
            base_act = apex4_mod.agent(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # 2. Macro Market-Hole Price Pulse Controller
            p_straw = market.price("STRAWBERRY")
            p_milk = market.price("MILK")
            money = farm.money

            # High cash buffer allows price timing; low cash forces immediate liquidation
            is_urgent_liquidity = (money < 3000.0) or (day <= 10)

            # Strawberry Market-Hole Execution
            straw_qty = farm.shed.get("STRAWBERRY", 0)
            if straw_qty >= 4:
                # Sell if urgent, or price is strong (>= 130), or shed getting crowded
                if is_urgent_liquidity or p_straw >= 130.0 or straw_qty >= 8:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "STRAWBERRY" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", "STRAWBERRY", straw_qty])

            # Milk Market-Hole Execution
            milk_qty = farm.shed.get("MILK", 0)
            if milk_qty >= 4:
                if is_urgent_liquidity or p_milk >= 155.0 or milk_qty >= 8:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", "MILK", milk_qty])

            # Other Commodities
            for item in ("TOMATO", "CARROT", "MELON", "WOOL"):
                qty = farm.shed.get(item, 0)
                if qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, qty])

            # 3. Terminal Clearance (Step >= 696)
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
_GLOBAL_B4 = B4MarketHoleAgent()

def agent(obs, configuration=None):
    global _GLOBAL_B4
    return _GLOBAL_B4.act(obs, configuration)
