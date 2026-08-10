"""L+ APEX 2.5-F: Marginal Counterfactual Value (MCV) Evaluator.
Computes incremental value of candidate actions relative to the exact expert baseline plan.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState, CROPS, ANIMALS

class MarginalActionEvaluator:
    """Evaluates the true marginal counterfactual advantage of a candidate action
    relative to what the L+ expert was already planning to execute.
    """

    @staticmethod
    def calculate_marginal_value(
        candidate: List[Any],
        expert_action: Dict[str, Any],
        state: WorldState
    ) -> Tuple[float, Dict[str, float]]:
        # 1. Safely unwrap orders
        first_cand = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_cand, list) and len(first_cand) > 0 and isinstance(first_cand[0], list):
            first_cand = first_cand[0]

        expert_market = list(expert_action.get("market", [])) if isinstance(expert_action, dict) else []

        # 2. Extract Candidate Order Parameters
        cand_cmd = first_cand[0] if len(first_cand) > 0 else "PASS"
        cand_item = first_cand[1] if len(first_cand) > 1 else "WHEAT"
        cand_qty = first_cand[2] if len(first_cand) > 2 else 1
        cand_price = float(state.prices.get(cand_item, 10.0))

        # 3. Find Overlapping Expert Order for the same item
        expert_qty = 0
        for ord in expert_market:
            if len(ord) > 1 and ord[0] == cand_cmd and ord[1] == cand_item:
                expert_qty = ord[2] if len(ord) > 2 else 1
                break

        # 4. Incremental Net Quantity & Raw Cash Delta
        delta_qty = cand_qty - expert_qty
        raw_cash_delta = delta_qty * cand_price

        # 5. Capital Enablement Multiplier (Is the cash utilized or idle?)
        # In Kaggriculture, idle cash in wallet without immediate investment has ~0 downstream elasticity
        current_money = state.money
        operating_reserve = state.cash_state.operating_reserve
        disposable_before = max(0.0, current_money - operating_reserve)
        disposable_after = max(0.0, (current_money + raw_cash_delta) - operating_reserve)

        # Check if cash delta unlocks a critical purchase threshold
        # Thresholds: HIRE ($100), BUY_SEED ($50), BUY_LAND ($500/$2000), BUY_ANIMAL ($400)
        unlocks_hire = (disposable_before < 100 <= disposable_after)
        unlocks_seed = (disposable_before < 50 <= disposable_after)
        unlocks_land = (disposable_before < 500 <= disposable_after)
        unlocks_animal = (disposable_before < 400 <= disposable_after)

        if unlocks_hire:
            capital_multiplier = 0.50  # Unlocks high-ROI worker
        elif unlocks_seed:
            capital_multiplier = 0.35  # Unlocks crop planting
        elif unlocks_land or unlocks_animal:
            capital_multiplier = 0.25  # Unlocks land/animal expansion
        else:
            # Idle cash with no threshold crossing: low marginal value
            # Only spot price timing difference (e.g. 1-2% price variance advantage)
            capital_multiplier = 0.02

        marginal_cash_value = raw_cash_delta * capital_multiplier

        # 6. Inventory Rotation & Congestion Relief Utility
        # Selling 1 wheat from full inventory relieves storage/tile congestion
        if cand_cmd == "SELL" and cand_item in ("WHEAT", "CARROT", "TOMATO") and expert_qty == 0:
            congestion_relief_adv = 3.50
        else:
            congestion_relief_adv = 0.0

        # 7. Total Marginal Counterfactual Value
        mcv = marginal_cash_value + congestion_relief_adv

        breakdown = {
            "delta_qty": float(delta_qty),
            "raw_cash_delta": raw_cash_delta,
            "capital_multiplier": capital_multiplier,
            "marginal_cash_value": marginal_cash_value,
            "congestion_relief_adv": congestion_relief_adv,
            "total_mcv": mcv
        }

        return mcv, breakdown
