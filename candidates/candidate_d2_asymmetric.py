"""Candidate D.2-A: Step 120 Land-2 Adaptive Melon Hedge Engine.

Implements the EXP106 Early Decision Boundary (t* = Step 120 / Day 5):
- At Step 120 (when Land #2 is acquired):
  Checks macro spawn price ratio: P_melon / P_straw >= 1.85.
- If and ONLY if condition met:
  Allocates a small hedge (4 or 8 plots) on Land #2 to high-margin Melons.
- Otherwise:
  Remains 100% monolithic Variant D.1 (38 Strawberries + 8 Cows + 13 Workers).
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import copy

from engine.agent import VariantDAgent

class CandidateD2AsymmetricAgent(VariantDAgent):
    """Candidate D.2-A: Step 120 Adaptive Hedge Agent."""

    def __init__(self, hedge_plots: int = 4, force_off: bool = False):
        super().__init__()
        self.hedge_plots = hedge_plots
        self.force_off = force_off
        self.hedge_active = False
        self.melon_seeds_bought = 0
        self.melon_plots_planted = 0

    def evaluate_step120_trigger(self, raw_obs: Dict[str, Any]):
        if self.force_off or self.hedge_plots <= 0:
            self.hedge_active = False
            return

        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)
        
        # We latch the decision at the Step 120 decision boundary (Steps 72 to 192)
        if step < 72:
            return

        market = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
        prices = market.get("prices", {}) if isinstance(market, dict) else {}
        p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
        p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

        ratio = p_melon / p_straw if p_straw > 0 else 1.0

        # High-precision ratio threshold from EXP106 (>= 1.85x)
        if ratio >= 1.85 and p_melon >= 240.0:
            self.hedge_active = True
        else:
            if step <= 144:
                self.hedge_active = False

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.evaluate_step120_trigger(raw_obs)
        base_act = super().act(raw_obs, raw_config)

        if not self.hedge_active:
            return base_act

        act = copy.deepcopy(base_act)
        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)

        farms = raw_obs.get("farms", [])
        my_farm = farms[0] if farms else {}
        money = float(my_farm.get("money", 0.0))
        inventory = my_farm.get("inventory", {})

        melon_seeds = inventory.get("MELON_SEED", inventory.get(3, 0)) if isinstance(inventory, dict) else 0

        # Step 120-200: Procure Melon seeds for Land #2
        if 96 <= step <= 240:
            if melon_seeds < self.hedge_plots and money >= 200.0 and self.melon_seeds_bought < self.hedge_plots:
                needed = self.hedge_plots - self.melon_seeds_bought
                orders = act.get("market_orders", [])
                has_melon_order = any(o.get("item") in ["MELON_SEED", 3, "melon_seed"] for o in orders if isinstance(o, dict))
                if not has_melon_order:
                    orders.append({"action": "BUY", "item": "MELON_SEED", "quantity": needed})
                    act["market_orders"] = orders
                    self.melon_seeds_bought += needed

            # Divert Land #2 strawberry plantings to Melons
            workers = act.get("worker_orders", [])
            for w_act in workers:
                if isinstance(w_act, dict) and self.melon_plots_planted < self.hedge_plots:
                    tool = w_act.get("tool") or w_act.get("item")
                    if tool in ["STRAWBERRY_SEED", 1, "strawberry_seed"] and melon_seeds > 0:
                        w_act["tool"] = "MELON_SEED"
                        w_act["item"] = "MELON_SEED"
                        self.melon_plots_planted += 1

        return act

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2AsymmetricAgent(hedge_plots=4, force_off=False)
    return agent._instance.act(obs, configuration)
