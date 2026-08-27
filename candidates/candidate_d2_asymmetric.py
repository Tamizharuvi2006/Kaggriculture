"""Candidate D.2-A: High-Precision Multi-Signal Trigger Quality Engine.

Implements strict 3-condition Trigger Quality Gating:
1. Opponent Portfolio Sensor:
   - Inspects opponent farm plots: Opponent has >= 2 non-strawberry arable plots or alternative commodities.
2. Macro Town Price Divergence Sensor:
   - Strawberry town price is depressed: P_straw < $110.00.
   - Melon town price is premium: P_melon >= $235.00.
3. Arable Reallocation Execution:
   - When and ONLY when all 3 conditions are satisfied simultaneously:
     Reallocates 4 arable plots to high-margin Melons.
   - Otherwise, remains 100% monolithic 38-Strawberry + 8-Cow Variant D.1.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import copy

from engine.agent import VariantDAgent

class CandidateD2AsymmetricAgent(VariantDAgent):
    """Candidate D.2-A: Multi-Signal Trigger Quality Agent."""

    def __init__(self, force_trigger_off: bool = False):
        super().__init__()
        self.force_trigger_off = force_trigger_off
        self.asymmetric_active = False
        self.melon_seeds_bought = 0
        self.melon_plots_planted = 0

    def evaluate_multi_signal_trigger(self, raw_obs: Dict[str, Any]):
        if self.force_trigger_off:
            self.asymmetric_active = False
            return

        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)
        if step < 72 or step > 480:
            self.asymmetric_active = False
            return

        # Signal 1: Market Prices
        market = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
        prices = market.get("prices", {}) if isinstance(market, dict) else {}
        p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
        p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

        price_condition = (p_straw < 112.0 and p_melon >= 235.0)

        # Signal 2: Opponent Farm Inspection
        farms = raw_obs.get("farms", [])
        opp_farm = farms[1] if len(farms) > 1 else {}
        opp_inventory = opp_farm.get("inventory", {}) if isinstance(opp_farm, dict) else {}
        opp_plots = opp_farm.get("plots", []) if isinstance(opp_farm, dict) else []

        # Check if opponent has non-strawberry crops or livestock
        opp_has_alt = False
        non_straw_count = 0
        for p in opp_plots:
            if isinstance(p, dict):
                crop_type = p.get("crop_type") or p.get("crop")
                if crop_type and crop_type not in ["STRAWBERRY", 1, "strawberry", None]:
                    non_straw_count += 1

        if non_straw_count >= 2 or opp_inventory.get("MELON_SEED", 0) > 0 or opp_inventory.get("MELON", 0) > 0:
            opp_has_alt = True

        # Multi-signal conjunction
        if price_condition and opp_has_alt:
            self.asymmetric_active = True
        else:
            self.asymmetric_active = False

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.evaluate_multi_signal_trigger(raw_obs)
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
        agent._instance = CandidateD2AsymmetricAgent(force_trigger_off=False)
    return agent._instance.act(obs, configuration)
