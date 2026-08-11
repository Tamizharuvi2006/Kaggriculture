"""L+ APEX 3.0: Empirical State-Conditioned MCV Evaluator (Offline R&D Branch).
Computes state-conditioned marginal counterfactual value MCV(action | state)
calibrated from historical replay dataset (mcv_replay_dataset.json).
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState


class EmpiricalMarginalEvaluator:
    """State-Conditioned Empirical MCV Evaluator for APEX 3.0.
    Replaces static multipliers with state-dependent empirical multipliers.
    """

    @staticmethod
    def calculate_marginal_value(
        candidate: List[Any],
        expert_action: Dict[str, Any],
        state: WorldState
    ) -> Tuple[float, Dict[str, float]]:
        # 1. Unwrap candidate order
        first_cand = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_cand, list) and len(first_cand) > 0 and isinstance(first_cand[0], list):
            first_cand = first_cand[0]

        expert_market = list(expert_action.get("market", [])) if isinstance(expert_action, dict) else []

        # 2. Extract Action Details
        cand_cmd = first_cand[0] if len(first_cand) > 0 else "PASS"
        cand_item = first_cand[1] if len(first_cand) > 1 else "WHEAT"
        cand_qty = first_cand[2] if len(first_cand) > 2 else 1
        cand_price = float(state.prices.get(cand_item, 10.0))

        # 3. Find Overlapping Expert Order
        expert_qty = 0
        for ord in expert_market:
            if len(ord) > 1 and ord[0] == cand_cmd and ord[1] == cand_item:
                expert_qty = ord[2] if len(ord) > 2 else 1
                break

        delta_qty = cand_qty - expert_qty
        raw_cash_delta = delta_qty * cand_price

        # 4. Extract State Features
        step = state.step
        current_money = state.money
        num_workers = len(state.workers)
        num_tiles = len(state.tiles)

        # Storage & Inventory congestion ratio
        total_inv_count = sum(state.inventory.values())
        congestion_ratio = min(1.0, total_inv_count / max(1.0, float(num_tiles * 2)))

        # Threshold unlocks
        operating_reserve = state.cash_state.operating_reserve
        disposable_before = max(0.0, current_money - operating_reserve)
        disposable_after = max(0.0, (current_money + raw_cash_delta) - operating_reserve)

        unlocks_hire = (disposable_before < 100 <= disposable_after)
        unlocks_seed = (disposable_before < 50 <= disposable_after)
        unlocks_land = (disposable_before < 500 <= disposable_after)

        # 5. State-Conditioned Empirical Multiplier Estimation
        if unlocks_hire:
            capital_multiplier = 0.50
        elif unlocks_seed:
            capital_multiplier = 0.35
        elif unlocks_land:
            capital_multiplier = 0.25
        else:
            # Empirical Cash Bracket Conditioning
            if current_money < 300.0:
                # Severe Liquidity Distress: Low empirical elasticity (16.7% win rate)
                capital_multiplier = 0.005
            elif 300.0 <= current_money < 1500.0:
                capital_multiplier = 0.025
            else:
                capital_multiplier = 0.045

            # Item-Specific Time Window Conditioning
            if cand_item == "FERTILIZER":
                if step < 200:
                    # Early game fertilizer sales yield minimal downstream delta (+ $422 vs + $16.9k)
                    capital_multiplier = min(capital_multiplier, 0.005)
                elif step >= 500:
                    capital_multiplier = max(capital_multiplier, 0.05)

        marginal_cash_value = raw_cash_delta * capital_multiplier

        # 6. State-Conditioned Congestion Relief
        if cand_cmd == "SELL" and cand_item in ("WHEAT", "CARROT", "TOMATO") and expert_qty == 0:
            if congestion_ratio > 0.4 and current_money >= 300.0:
                congestion_relief_adv = 3.50 * congestion_ratio
            else:
                congestion_relief_adv = 0.0
        else:
            congestion_relief_adv = 0.0

        mcv = marginal_cash_value + congestion_relief_adv

        breakdown = {
            "delta_qty": float(delta_qty),
            "raw_cash_delta": raw_cash_delta,
            "capital_multiplier": capital_multiplier,
            "marginal_cash_value": marginal_cash_value,
            "congestion_relief_adv": congestion_relief_adv,
            "total_mcv": mcv,
            "step": step,
            "congestion_ratio": congestion_ratio,
        }

        return mcv, breakdown
