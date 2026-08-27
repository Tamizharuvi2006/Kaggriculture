"""Candidate D.2-A: Parameterized Asymmetric Intervention Engine.

Supports configurable Intervention Intensity (25%, 50%, 75%, 100%):
- Level 1 (25%): 4 Melon seeds, 2 plot planting conversions.
- Level 2 (50%): 8 Melon seeds, 4 plot planting conversions.
- Level 3 (75%): 12 Melon seeds, 6 plot planting conversions + continuous watering.
- Level 4 (100%): 16 Melon seeds, full SW quadrant (8 plots) dedicated Melon block.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import copy

from engine.agent import VariantDAgent

class CandidateD2AsymmetricAgent(VariantDAgent):
    """Candidate D.2-A: Parameterized Intensity Asymmetric Agent."""

    def __init__(self, intensity: float = 0.50):
        super().__init__()
        self.intensity = intensity  # 0.25, 0.50, 0.75, 1.00
        self.max_melon_seeds = int(16 * intensity)
        self.max_melon_plots = int(8 * intensity)
        self.asymmetric_active = False
        self.melon_seeds_bought = 0
        self.melon_plots_planted = 0

    def evaluate_regime(self, raw_obs: Dict[str, Any]):
        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)
        market = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
        prices = market.get("prices", {}) if isinstance(market, dict) else {}

        p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
        p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

        # Trigger on high-melon premium seeds during mid-game (Steps 72-480)
        if 72 <= step <= 480 and (p_melon >= 220.0 or p_straw < 118.0):
            self.asymmetric_active = True
        elif step > 480:
            self.asymmetric_active = False

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.evaluate_regime(raw_obs)
        base_act = super().act(raw_obs, raw_config)

        if not self.asymmetric_active:
            return base_act

        act = copy.deepcopy(base_act)
        farms = raw_obs.get("farms", [])
        my_farm = farms[0] if farms else {}
        money = float(my_farm.get("money", 0.0))
        inventory = my_farm.get("inventory", {})

        # Market Intervention: Seed procurement scaled by intensity
        melon_seeds = inventory.get("MELON_SEED", inventory.get(3, 0)) if isinstance(inventory, dict) else 0
        if melon_seeds < self.max_melon_plots and money >= 200.0 and self.melon_seeds_bought < self.max_melon_seeds:
            orders = act.get("market_orders", [])
            has_melon_order = any(o.get("item") in ["MELON_SEED", 3, "melon_seed"] for o in orders if isinstance(o, dict))
            if not has_melon_order:
                batch = min(4, self.max_melon_seeds - self.melon_seeds_bought)
                if batch > 0:
                    orders.append({"action": "BUY", "item": "MELON_SEED", "quantity": batch})
                    act["market_orders"] = orders
                    self.melon_seeds_bought += batch

        # Worker Intervention: Planting conversions scaled by intensity
        workers = act.get("worker_orders", [])
        for w_act in workers:
            if isinstance(w_act, dict) and self.melon_plots_planted < self.max_melon_plots:
                tool = w_act.get("tool") or w_act.get("item")
                if tool in ["STRAWBERRY_SEED", 1, "strawberry_seed"] and melon_seeds > 0:
                    w_act["tool"] = "MELON_SEED"
                    w_act["item"] = "MELON_SEED"
                    self.melon_plots_planted += 1

        return act

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2AsymmetricAgent(intensity=0.75)
    return agent._instance.act(obs, configuration)
