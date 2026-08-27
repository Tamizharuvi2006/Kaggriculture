"""Candidate D.2-B: High-Velocity Cashflow & Dynamic Liquidation Timing Engine.

Explores secondary cashflow timing and market liquidation execution:
1. Fluid Milk Cashflow:
   - Sells Milk at batch size >= 2 (or >= 1 when P_milk >= $190) rather than waiting for >= 4 units.
   - Accelerates cash reinvestment velocity and locks in peak dairy prices before duopoly saturation.
2. Dynamic Gradual Liquidation (Steps 648-720):
   - Initiates pre-terminal clearance on Day 27 (Step 648) instead of waiting for Step 696.
   - Sells inventory into high Day 27-28 town bids before market-wide Step 700+ fire-sales.
3. 100% Core Preservation:
   - Preserves 100% of the 38-Strawberry + 8-Cow + 13-Worker APEX spine.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional
import copy

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState

class CandidateD2TimingAgent(VariantDAgent):
    """Candidate D.2-B: Timing & Cashflow Optimization Agent."""

    def __init__(self, mode: str = "combined"):
        super().__init__()
        self.mode = mode.lower()  # 'control', 'fluid_milk', 'early_clearance', 'combined'

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.mode == "control":
            return super().act(raw_obs, raw_config)

        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            step = obs.step

            # 1. Base Master Action from APEX4 Spine
            base_act = super().act(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            market_data = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
            prices = market_data.get("prices", {}) if isinstance(market_data, dict) else {}
            p_milk = float(prices.get("MILK", prices.get(5, 190.0)) if isinstance(prices, dict) else 190.0)
            p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)

            # 2. Timing Modification A: Fluid Milk Cashflow
            if self.mode in ("fluid_milk", "combined"):
                milk_qty = farm.shed.get("MILK", 0)
                # Sell milk earlier if price is strong or batch is >= 2
                if (milk_qty >= 2) or (milk_qty >= 1 and p_milk >= 195.0 and step >= 200):
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "MILK" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", "MILK", milk_qty])

            # 3. Timing Modification B: Dynamic Gradual Liquidation (Step >= 648 / Day 27)
            if self.mode in ("early_clearance", "combined"):
                if 648 <= step < 696:
                    # Clear strawberries and milk if price is favorable
                    for item, cur_p, min_p in [("STRAWBERRY", p_straw, 110.0), ("MILK", p_milk, 175.0), ("FERTILIZER", 10.0, 5.0)]:
                        qty = farm.shed.get(item, 0)
                        if qty >= 2 and cur_p >= min_p:
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
        agent._instance = CandidateD2TimingAgent(mode="combined")
    return agent._instance.act(obs, configuration)
