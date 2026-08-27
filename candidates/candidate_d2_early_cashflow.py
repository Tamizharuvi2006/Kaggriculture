"""Candidate D.2-EarlyCash: Early Starter Inventory Liquidation Optimization.

Micro-optimization on top of Variant D.1 Control A:
- Liquidates idle starter inventory (WHEAT, FERTILIZER) on Days 1-5 (Steps 0-120) whenever available (qty >= 1).
- Converts deadweight opening assets into active liquid capital to accelerate opening worker hires and Land #2 acquisition.
- Preserves 100% of the 38-Strawberry + 8-Cow spatial and planting spine.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState

class CandidateD2EarlyCashAgent(VariantDAgent):
    """Variant D.2 Candidate: Early Cashflow Optimization."""

    def __init__(self):
        super().__init__()

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            step = obs.step
            day = obs.day

            base_act = super().act(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            # Early Starter Liquidation (Days 1 to 5)
            if day <= 5:
                for item in ("WHEAT", "FERTILIZER"):
                    qty = farm.shed.get(item, 0)
                    if qty >= 1:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", item, qty])

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders[:10],
            }
        except Exception:
            return super().act(raw_obs, raw_config)

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2EarlyCashAgent()
    return agent._instance.act(obs, configuration)
