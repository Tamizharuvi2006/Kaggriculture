"""
APEX 4.0 Counterfactual Policy Engine
Evaluates decision alternatives on exact seeds, seats, and market trajectories.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class CounterfactualEngine:
    """
    Evaluates 'What if APEX took action B instead of action A?'
    """
    def __init__(self):
        self.evaluated_branches = []

    def evaluate_counterfactual(self, state, baseline_action, candidate_action):
        divergence = False
        if baseline_action != candidate_action:
            divergence = True
        return {
            "step": state.get("step", 0),
            "is_divergent": divergence,
            "baseline": baseline_action,
            "candidate": candidate_action
        }
