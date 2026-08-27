"""Candidate D.2-A: Configurable Signal Ablation Engine.

Supports 5 Ablation Configurations:
- Mode 'A' (S1 only): Opponent Portfolio Divergence (>= 1 non-strawberry crop/item).
- Mode 'B' (S1 + S2): Opponent Portfolio + Strawberry Price <= $125.
- Mode 'C' (S1 + S3): Opponent Portfolio + Melon Price >= $210.
- Mode 'D' (S2 + S3): Macro Price Divergence only (P_straw <= $120 AND P_melon >= $220).
- Mode 'E' (S1 + S2 + S3): Strict 3-signal conjunction.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import copy

from engine.agent import VariantDAgent

class CandidateD2AsymmetricAgent(VariantDAgent):
    """Candidate D.2-A: Signal Ablation Agent."""

    def __init__(self, mode: str = "A"):
        super().__init__()
        self.mode = mode.upper()  # 'A', 'B', 'C', 'D', 'E'
        self.asymmetric_active = False
        self.melon_seeds_bought = 0
        self.melon_plots_planted = 0

    def evaluate_signals(self, raw_obs: Dict[str, Any]):
        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)
        if step < 72 or step > 480:
            self.asymmetric_active = False
            return

        # S1: Opponent Portfolio Divergence
        farms = raw_obs.get("farms", [])
        opp_farm = farms[1] if len(farms) > 1 else {}
        opp_inventory = opp_farm.get("inventory", {}) if isinstance(opp_farm, dict) else {}
        opp_plots = opp_farm.get("plots", []) if isinstance(opp_farm, dict) else []

        non_straw_count = 0
        for p in opp_plots:
            if isinstance(p, dict):
                crop_type = p.get("crop_type") or p.get("crop")
                if crop_type and crop_type not in ["STRAWBERRY", 1, "strawberry", None]:
                    non_straw_count += 1

        has_alt_inv = any(opp_inventory.get(k, 0) > 0 for k in ["MELON", "MELON_SEED", "TOMATO", "TOMATO_SEED", 3, 2])
        s1 = (non_straw_count >= 1 or has_alt_inv)

        # S2 & S3: Macro Price Signals
        market = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
        prices = market.get("prices", {}) if isinstance(market, dict) else {}
        p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
        p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

        s2 = (p_straw <= 125.0)
        s3 = (p_melon >= 210.0)

        # Evaluate Mode
        if self.mode == "A":
            self.asymmetric_active = s1
        elif self.mode == "B":
            self.asymmetric_active = (s1 and s2)
        elif self.mode == "C":
            self.asymmetric_active = (s1 and s3)
        elif self.mode == "D":
            self.asymmetric_active = (s2 and s3)
        elif self.mode == "E":
            self.asymmetric_active = (s1 and s2 and s3)
        else:
            self.asymmetric_active = False

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.evaluate_signals(raw_obs)
        base_act = super().act(raw_obs, raw_config)

        if not self.asymmetric_active:
            return base_act

        act = copy.deepcopy(base_act)
        farms = raw_obs.get("farms", [])
        my_farm = farms[0] if farms else {}
        money = float(my_farm.get("money", 0.0))
        inventory = my_farm.get("inventory", {})

        melon_seeds = inventory.get("MELON_SEED", inventory.get(3, 0)) if isinstance(inventory, dict) else 0
        if melon_seeds < 4 and money >= 200.0 and self.melon_seeds_bought < 4:
            orders = act.get("market_orders", [])
            has_melon_order = any(o.get("item") in ["MELON_SEED", 3, "melon_seed"] for o in orders if isinstance(o, dict))
            if not has_melon_order:
                orders.append({"action": "BUY", "item": "MELON_SEED", "quantity": 4})
                act["market_orders"] = orders
                self.melon_seeds_bought += 4

        workers = act.get("worker_orders", [])
        for w_act in workers:
            if isinstance(w_act, dict) and self.melon_plots_planted < 4:
                tool = w_act.get("tool") or w_act.get("item")
                if tool in ["STRAWBERRY_SEED", 1, "strawberry_seed"] and melon_seeds > 0:
                    w_act["tool"] = "MELON_SEED"
                    w_act["item"] = "MELON_SEED"
                    self.melon_plots_planted += 1

        return act

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2AsymmetricAgent(mode="A")
    return agent._instance.act(obs, configuration)
