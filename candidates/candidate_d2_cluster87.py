"""Candidate D.2-C: Factorized Cluster 87 Engine.

Supports 6 Factorized Replication Arms:
- Mode 'A' (control): Pure Variant D.1 Control A.
- Mode 'B' (early_cash): Fast Days 1-5 Wheat & Fertilizer sales to maximize worker ramp cash velocity.
- Mode 'C' (melon_spike): Day 0 Opening Melons (11 seeds) liquidated on Day 11 for a $15k liquidity injection.
- Mode 'D' (dual_livestock): Dual Herd (8 Cows + 6 Sheep) capturing both Milk and Wool demand baskets.
- Mode 'E' (wheat_filler): High-Velocity Arable Utilization (plants 2-day Wheat on vacant/idle plots).
- Mode 'F' (full_cluster87): Integrated 4-pillar Cluster 87 reproduction.
"""
from __future__ import annotations
import sys
import os
from typing import Dict, Any, Optional, List
import copy

from engine.agent import VariantDAgent
from engine.state.observation import Observation
from engine.state.farm_state import FarmState

class CandidateD2Cluster87Agent(VariantDAgent):
    """Candidate D.2-C: Factorized Cluster 87 Replication Agent."""

    def __init__(self, mode: str = "A"):
        super().__init__()
        self.mode = mode.upper()  # 'A', 'B', 'C', 'D', 'E', 'F'
        self.day0_melon_bought = 0
        self.day0_melon_planted = 0
        self.wheat_filler_planted = 0
        self.sheep_bought = 0

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.mode == "A":
            return super().act(raw_obs, raw_config)

        try:
            obs = Observation(raw_obs, raw_config)
            farm = FarmState(obs)
            step = obs.step
            day = obs.day
            hour = obs.hour

            base_act = super().act(raw_obs, raw_config)
            if not isinstance(base_act, dict):
                return base_act

            farmer_act = list(base_act.get("farmer") or ["PASS"])
            hands_act = [list(h) for h in (base_act.get("hands") or [])]
            market_orders = list(base_act.get("market") or [])

            farms = raw_obs.get("farms", [])
            my_farm = farms[0] if farms else {}
            money = float(my_farm.get("money", 0.0))
            inventory = my_farm.get("inventory", {})

            # --- PILLAR 1: EARLY CASH-FLOW (Modes B, F) ---
            if self.mode in ("B", "F"):
                if day <= 5:
                    for item in ("WHEAT", "FERTILIZER"):
                        qty = farm.shed.get(item, 0)
                        if qty >= 1:
                            if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == item for m in market_orders):
                                if len(market_orders) < 10:
                                    market_orders.append(["SELL", item, qty])

            # --- PILLAR 2: DAY-11 MELON SPIKE (Modes C, F) ---
            if self.mode in ("C", "F"):
                # Buy 11 melon seeds on Day 0/1
                if step < 48 and self.day0_melon_bought < 11 and money >= 80.0:
                    needed = 11 - self.day0_melon_bought
                    if not any(len(m) >= 2 and m[0] == "BUY" and m[1] in ("MELON_SEED", 3, "melon_seed") for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["BUY", "MELON_SEED", min(needed, int(money // 80))])
                            self.day0_melon_bought += min(needed, int(money // 80))

                # Liquidate all melons on Day 11
                if 240 <= step < 288:
                    melon_qty = farm.shed.get("MELON", 0)
                    if melon_qty >= 1:
                        if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "MELON" for m in market_orders):
                            if len(market_orders) < 10:
                                market_orders.append(["SELL", "MELON", melon_qty])

            # --- PILLAR 3: DUAL LIVESTOCK (Modes D, F) ---
            if self.mode in ("D", "F"):
                # Sell Wool alongside milk
                wool_qty = farm.shed.get("WOOL", 0)
                if wool_qty >= 2:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "WOOL" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", "WOOL", wool_qty])

            # --- PILLAR 4: IDLE-TILE WHEAT FILLER (Modes E, F) ---
            if self.mode in ("E", "F"):
                wheat_seeds = inventory.get("WHEAT_SEED", inventory.get(0, 0))
                # Buy wheat seeds in small batches if low
                if wheat_seeds < 4 and money >= 50.0 and day <= 24:
                    if not any(len(m) >= 2 and m[0] == "BUY" and m[1] in ("WHEAT_SEED", 0, "wheat_seed") for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["BUY", "WHEAT_SEED", 4])

                # Regular wheat liquidation
                wheat_qty = farm.shed.get("WHEAT", 0)
                if wheat_qty >= 4:
                    if not any(len(m) >= 2 and m[0] == "SELL" and m[1] == "WHEAT" for m in market_orders):
                        if len(market_orders) < 10:
                            market_orders.append(["SELL", "WHEAT", wheat_qty])

            return {
                "farmer": farmer_act,
                "hands": hands_act,
                "market": market_orders[:10],
            }
        except Exception:
            return super().act(raw_obs, raw_config)

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2Cluster87Agent(mode="A")
    return agent._instance.act(obs, configuration)
