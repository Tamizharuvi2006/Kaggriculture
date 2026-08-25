"""Candidate EXP059: Regime-Aware Supply Shaping (RASS-1).
Dynamically shapes post-harvest market supply tranches based on detected market absorption:
1. Reinvestment Invariant:
   - Tranche 1 (19 units) is ALWAYS sold immediately upon harvest.
   - 19 units * $140+ = $2,660+ cash, instantly securing the $475 required for Wave N+1 seeds.
2. Regime-Aware Staggering for Tranche 2:
   - ELITE (Fast Town Drain): Tranche 2 (remaining units) sold 12 steps later after opponent dump is absorbed.
   - STANDARD (Moderate Drain): Tranche 2 sold 16 steps later.
   - CRASH (Slow Drain / High Risk): Tranche 2 sold immediately (Pure D.1 fallback to prevent inventory congestion).
3. Endgame Minimax Guarantee:
   - At Step >= 696: All remaining inventory is liquidated immediately via the 24-step minimax drain buffer.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState

class RegimeAwareSupplyShaper:
    """Manages post-harvest supply tranches to avoid duopoly price depression."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.stagger_queue: Dict[str, int] = {} # item -> step when Tranche 2 is allowed to sell
        self.tranche1_sales = 0
        self.tranche2_sales = 0
        self.tranche1_revenue = 0.0
        self.tranche2_revenue = 0.0

    def process_orders(self, obs: Observation, farm: FarmState, base_act: Dict[str, Any]) -> Dict[str, Any]:
        step = obs.step
        farmer_cmd = list(base_act.get("farmer") or ["PASS"])
        hands_cmds = [list(h) for h in (base_act.get("hands") or [])]
        market_orders = list(base_act.get("market") or [])

        # 1. Endgame Clearance (Step >= 696): Minimax 24-step liquidation bypass
        if step >= 696:
            for item, qty in farm.shed.items():
                if int(qty or 0) > 0:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", item, int(qty)])
            return {"farmer": farmer_cmd, "hands": hands_cmds, "market": market_orders[:10]}

        # 2. Detect Market Regime from Town Unlocked Shops & Total Pie
        town = getattr(obs, "town", {}) or {}
        unlocked_shops = list(town.get("unlocked_shops") or []) if isinstance(town, dict) else []
        straw_shops = {"SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET"}
        has_straw_shop = any(s in straw_shops for s in unlocked_shops)

        # Tranche 2 delay: Elite = 12 steps, Standard = 16 steps, Crash = 0 (Immediate)
        if len(unlocked_shops) >= 2 and has_straw_shop:
            delay_steps = 12 # Elite
        elif len(unlocked_shops) >= 1:
            delay_steps = 16 # Standard
        else:
            delay_steps = 0  # Crash / Early

        # 3. Supply-Shaping for Strawberries and High-Volume Commodities
        for item in ("STRAWBERRY", "MILK", "TOMATO", "CARROT", "WOOL"):
            qty = int(farm.shed.get(item, 0) or 0)
            if qty >= 4:
                # Check if item is currently in stagger delay for Tranche 2
                allowed_step = self.stagger_queue.get(item, 0)
                
                if item == "STRAWBERRY" and qty >= 30 and delay_steps > 0:
                    # Stagger into Tranche 1 (19 units now) + Tranche 2 (19 units later)
                    if step >= allowed_step:
                        # Sell Tranche 1
                        tranche1_qty = min(19, qty)
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, tranche1_qty])
                                self.tranche1_sales += 1
                                self.stagger_queue[item] = step + delay_steps
                else:
                    # Standard batch sell if delay has passed or not staggered
                    if step >= allowed_step:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])
                                self.tranche2_sales += 1
                                self.stagger_queue.pop(item, None)

        return {
            "farmer": farmer_cmd,
            "hands": hands_cmds,
            "market": market_orders[:10],
        }

class RASSAgent:
    """Agent equipped with Regime-Aware Supply Shaping."""
    def __init__(self):
        self.d1_agent = VariantDAgent()
        self.shaper = RegimeAwareSupplyShaper()

    def reset(self):
        self.d1_agent.reset()
        self.shaper.reset()

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        obs = Observation(raw_obs, raw_config)
        farm = FarmState(obs)

        # 1. Base D.1 action
        base_act = self.d1_agent.act(raw_obs, raw_config)
        if not isinstance(base_act, dict):
            return base_act

        # 2. Apply Supply-Shaping order filter
        return self.shaper.process_orders(obs, farm, base_act)

_GLOBAL_RASS_AGENT = RASSAgent()

def agent(obs, configuration=None):
    global _GLOBAL_RASS_AGENT
    return _GLOBAL_RASS_AGENT.act(obs, configuration)
