"""L+ APEX 2.5-G: Counterfactual State Simulation Engine with Marginal Counterfactual Value (MCV) & UCB.
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState
from apex.action_safety import ActionSafetyGate
from apex.marginal_evaluator import MarginalActionEvaluator

class CandidateRejectionTelemetry:
    """Tracks detailed breakdown of candidate rejection reasons across decisions."""
    def __init__(self):
        self.total_generated = 0
        self.rejections: Dict[str, int] = {
            "REJECT_LIQUIDITY": 0,
            "REJECT_WORKER": 0,
            "REJECT_TERMINAL": 0,
            "REJECT_VALUE": 0,
            "REJECT_CONFIDENCE": 0,
            "REJECT_DUPLICATE": 0,
            "PASSED": 0
        }
        self.action_counts: Dict[str, int] = {}

    def log_rejection(self, reason_category: str):
        self.total_generated += 1
        cat = reason_category if reason_category in self.rejections else "REJECT_VALUE"
        self.rejections[cat] += 1

    def log_passed(self):
        self.total_generated += 1
        self.rejections["PASSED"] += 1

    def get_audit_summary(self) -> Dict[str, Any]:
        total = max(1, self.total_generated)
        return {
            "total_generated": self.total_generated,
            "passed_pct": (self.rejections["PASSED"] / total) * 100.0,
            "rejections": {k: (v / total) * 100.0 for k, v in self.rejections.items()}
        }

class CounterfactualSimulator:
    """Counterfactual Simulator Engine with Marginal Counterfactual Value (MCV) & Calibrated UCB Exploration."""

    REJECTION_TELEMETRY = CandidateRejectionTelemetry()

    @staticmethod
    def evaluate_exploration_candidate(
        candidate: List[Any],
        expert_action: Dict[str, Any],
        state: WorldState,
        confidence_threshold: float = 0.10
    ) -> Tuple[bool, float, str]:
        # 1. Action Safety Gate Check
        is_safe, safety_reason = ActionSafetyGate.is_action_safe(candidate, state)
        if not is_safe:
            if "LIQUIDITY" in safety_reason:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_LIQUIDITY")
            elif "TERMINAL" in safety_reason:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_TERMINAL")
            elif "HIRE" in safety_reason or "WORKER" in safety_reason:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_WORKER")
            else:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_VALUE")
            return False, 0.0, f"REJECTED_BY_SAFETY_GATE: {safety_reason}"

        # 2. Marginal Counterfactual Action Value (MCV) Scoring
        mcv_score, breakdown = MarginalActionEvaluator.calculate_marginal_value(candidate, expert_action, state)

        # UCB Bonus: Uncertainty bonus calibrated for MCV scale ($0 - $10)
        action_key = str(candidate[0])
        n_obs = CounterfactualSimulator.REJECTION_TELEMETRY.action_counts.get(action_key, 0)
        ucb_bonus = 2.50 / math.sqrt(n_obs + 1.0)
        total_mcv_score = mcv_score + ucb_bonus

        confidence = min(1.0, total_mcv_score / 15.0)

        # 3. MCV Exploration Eligibility: Safe + Non-negative Marginal Delta
        if total_mcv_score >= 1.0 and confidence >= confidence_threshold:
            CounterfactualSimulator.REJECTION_TELEMETRY.log_passed()
            CounterfactualSimulator.REJECTION_TELEMETRY.action_counts[action_key] = n_obs + 1
            return True, total_mcv_score, f"APPROVED_MCV_{mcv_score:.2f}_CONF_{confidence:.2f}"
        else:
            if confidence < confidence_threshold:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_CONFIDENCE")
            else:
                CounterfactualSimulator.REJECTION_TELEMETRY.log_rejection("REJECT_VALUE")
            return False, total_mcv_score, f"REJECTED_MCV_{total_mcv_score:.2f}"
