"""L+ APEX 2.5-E: Calibrated Bayesian Experience Memory.
Stores rich state-action-outcome tuples including prediction error and regime context.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
from apex.world_model import WorldState

class ExperienceRecord:
    def __init__(
        self,
        step: int,
        action_key: str,
        regime: str,
        predicted_value: float,
        actual_delta: float,
        prediction_error: float,
        situation_features: Dict[str, float],
        confidence: float = 0.20
    ):
        self.step = step
        self.action_key = action_key
        self.regime = regime
        self.predicted_value = predicted_value
        self.actual_delta = actual_delta
        self.prediction_error = prediction_error
        self.situation_features = situation_features
        self.confidence = confidence

class ExperienceMemory:
    """Stores past match experiences with prediction error calibration and regime awareness."""

    def __init__(self):
        self.records: List[ExperienceRecord] = []

    def add_experience(
        self,
        step: int,
        action_key: str,
        regime: str,
        predicted_value: float,
        actual_delta: float,
        situation_features: Dict[str, float],
        confidence: float = 0.20
    ):
        """Appends a new calibrated empirical divergence observation into experience memory."""
        error = actual_delta - predicted_value
        self.records.append(ExperienceRecord(
            step=step,
            action_key=action_key,
            regime=regime,
            predicted_value=predicted_value,
            actual_delta=actual_delta,
            prediction_error=error,
            situation_features=situation_features,
            confidence=confidence
        ))

    def get_calibration_summary(self) -> Dict[str, Any]:
        if not self.records:
            return {"total_records": 0, "mae": 0.0, "bias": 0.0, "correlation": 0.0}

        errors = [r.prediction_error for r in self.records]
        preds = [r.predicted_value for r in self.records]
        actuals = [r.actual_delta for r in self.records]

        n = len(self.records)
        mae = sum(abs(e) for e in errors) / n
        bias = sum(errors) / n

        # Correlation between predicted and actual
        mean_p = sum(preds) / n
        mean_a = sum(actuals) / n
        num = sum((p - mean_p) * (a - mean_a) for p, a in zip(preds, actuals))
        den = math.sqrt(sum((p - mean_p) ** 2 for p in preds) * sum((a - mean_a) ** 2 for a in actuals))
        corr = (num / den) if den > 1e-6 else 0.0

        return {
            "total_records": n,
            "mae": mae,
            "bias": bias,
            "correlation": corr,
            "records": [
                {
                    "step": r.step,
                    "action": r.action_key,
                    "regime": r.regime,
                    "predicted": r.predicted_value,
                    "actual": r.actual_delta,
                    "error": r.prediction_error
                }
                for r in self.records
            ]
        }

    def calculate_adjustment(self, state: WorldState, action_type: str) -> float:
        total_adjustment = 0.0
        for rec in self.records:
            if action_type in rec.action_key:
                step_diff = abs(state.step - rec.step)
                step_sim = math.exp(-step_diff / 48.0)
                rem_sim = max(0.0, 1.0 - abs(state.remaining_steps - rec.situation_features.get("remaining_steps", 20.0)) / 100.0)
                total_sim = step_sim * rem_sim
                if total_sim > 0.1:
                    adj = total_sim * rec.confidence * rec.actual_delta
                    total_adjustment += adj
        return total_adjustment
