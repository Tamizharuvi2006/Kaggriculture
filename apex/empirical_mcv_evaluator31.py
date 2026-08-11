"""L+ APEX 3.1: Environment-Parity Calibrated Empirical MCV Evaluator.
Calibrated specifically for Kaggle Live Server Market Dynamics:
- townCenterSellInterval = 24 (Town Center clears inventory once per 24-step day).
- 24-Step Inventory Absorption Delay & Liquidity Multipliers.
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState

class EmpiricalMarginalEvaluator31:
    """State-Conditioned Empirical MCV Evaluator for APEX 3.1 (Kaggle Parity)."""

    @staticmethod
    def calculate_marginal_value(
        candidate: List[Any],
        expert_action: Dict[str, Any],
        state: WorldState
    ) -> Tuple[float, Dict[str, float]]:
        first_cand = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_cand, list) and len(first_cand) > 0 and isinstance(first_cand[0], list):
            first_cand = first_cand[0]

        expert_market = list(expert_action.get("market", [])) if isinstance(expert_action, dict) else []

        cand_cmd = first_cand[0] if len(first_cand) > 0 else "PASS"
        cand_item = first_cand[1] if len(first_cand) > 1 else "WHEAT"
        cand_qty = first_cand[2] if len(first_cand) > 2 else 1
        cand_price = float(state.prices.get(cand_item, 10.0))

        expert_qty = 0
        for ord in expert_market:
            if len(ord) > 1 and ord[0] == cand_cmd and ord[1] == cand_item:
                expert_qty = ord[2] if len(ord) > 2 else 1
                break

        delta_qty = cand_qty - expert_qty
        raw_cash_delta = delta_qty * cand_price

        step = state.step
        current_money = state.money
        num_tiles = max(1, len(state.tiles))

        total_inv_count = sum(state.inventory.values())
        congestion_ratio = min(1.0, total_inv_count / max(1.0, float(num_tiles * 2)))

        operating_reserve = 300.0 if state.day <= 20 else 150.0
        disposable_before = max(0.0, current_money - operating_reserve)
        disposable_after = max(0.0, (current_money + raw_cash_delta) - operating_reserve)

        unlocks_hire = (disposable_before < 100 <= disposable_after)
        unlocks_seed = (disposable_before < 50 <= disposable_after)
        unlocks_land = (disposable_before < 500 <= disposable_after)

        # 24-Step Parity Correction: Inventory clearing delay lowers raw liquidity velocity
        # Low-cash selling (< $300) under 24-step clearing incurs heavier price suppression penalty
        if unlocks_hire:
            capital_multiplier = 0.45
        elif unlocks_seed:
            capital_multiplier = 0.30
        elif unlocks_land:
            capital_multiplier = 0.20
        else:
            if current_money < 300.0:
                capital_multiplier = 0.002 # Heavier 24-step distress penalty
            elif 300.0 <= current_money < 1500.0:
                capital_multiplier = 0.018
            else:
                capital_multiplier = 0.035

            if cand_item == "FERTILIZER":
                if step < 200:
                    capital_multiplier = min(capital_multiplier, 0.002)
                elif step >= 500:
                    capital_multiplier = max(capital_multiplier, 0.04)

        marginal_cash_value = raw_cash_delta * capital_multiplier

        # Congestion relief: 24-step Town Center clearance means warehouse congestion is relieved slower
        if cand_cmd == "SELL" and cand_item in ("WHEAT", "CARROT", "TOMATO") and expert_qty == 0:
            if congestion_ratio > 0.45 and current_money >= 300.0:
                congestion_relief_adv = 2.80 * congestion_ratio
            else:
                congestion_relief_adv = 0.0
        else:
            congestion_relief_adv = 0.0

        mcv = marginal_cash_value + congestion_relief_adv
        return mcv, {"total_mcv": mcv, "capital_multiplier": capital_multiplier}
