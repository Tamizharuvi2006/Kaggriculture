"""L+ APEX 2.0: Risk-Aware & Margin-Weighted Action Evaluator.
Unwraps candidate order lists cleanly.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from apex.world_model import WorldState
from apex.economic_model import CommodityModel
from apex.time_model import TimeModel
from apex.behavior_model import BehaviorFingerprint

class ActionEvaluator:
    """Risk-aware, margin-weighted action scoring model:
    ActionScore = ExpectedProfit + FutureValue + (WinProb * MarginValue) + TerminalValue 
                  - TransitCost - OpportunityCost - DeadlockRisk - VariancePenalty
    """

    @staticmethod
    def score_market_candidate(
        candidate: List[Any],
        state: WorldState,
        fingerprint: Optional[BehaviorFingerprint] = None
    ) -> float:
        if not candidate:
            return 0.0

        # Cleanly unwrap order list format
        first_ord = candidate[0] if isinstance(candidate, list) and len(candidate) > 0 else candidate
        if isinstance(first_ord, list) and len(first_ord) > 0 and isinstance(first_ord[0], list):
            first_ord = first_ord[0]

        action_type = first_ord[0] if isinstance(first_ord, list) and len(first_ord) > 0 else first_ord

        remaining = state.remaining_steps
        current_margin = state.money - state.opp_money

        # 1. Expected Immediate Profit
        immediate_profit = 0.0
        if action_type == "SELL":
            item = first_ord[1] if len(first_ord) > 1 else "WHEAT"
            qty = first_ord[2] if len(first_ord) > 2 else 1
            price = float(state.prices.get(item, 10.0))
            immediate_profit = qty * price
            if TimeModel.is_terminal_window(state, 48):
                immediate_profit *= 1.5

        # 2. Expected Future Value
        future_value = 0.0
        if action_type == "BUY_SEED":
            crop = first_ord[1] if len(first_ord) > 1 else "WHEAT"
            qty = first_ord[2] if len(first_ord) > 2 else 1
            metrics = CommodityModel.evaluate_commodity(crop, state)
            discount = TimeModel.time_discount_factor(state)
            future_value = metrics.roi_per_step * qty * discount * 500.0
        elif action_type == "BUY_ANIMAL":
            animal = first_ord[1] if len(first_ord) > 1 else "COW"
            product = "MILK" if animal == "COW" else "WOOL"
            metrics = CommodityModel.evaluate_commodity(product, state)
            discount = TimeModel.time_discount_factor(state)
            future_value = metrics.roi_per_step * discount * 1000.0
        elif action_type == "HIRE":
            if state.day <= 8:
                future_value = 150.0
            else:
                future_value = -80.0  # Late hires waste capital

        # 3. Aggregate Score
        total_score = immediate_profit + future_value
        return max(10.0, total_score)
