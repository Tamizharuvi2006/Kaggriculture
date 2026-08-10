"""Trace turn 100 in detail to see why candidates are rejected or not chosen.
"""

from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.agent import _POLICY, WorldState
from apex.planner import ActionPlanner
from apex.counterfactual import CounterfactualSimulator
from apex.action_safety import ActionSafetyGate
from apex.evaluator import ActionEvaluator

def trace_turn_100():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})
    obs = env.reset()[0]["observation"]
    obs["step"] = 100
    obs["day"] = 100 // 24
    obs["hour"] = 100 % 24

    state = WorldState(obs)
    print(f"Step: {state.step}, Money: {state.money}, Inventory: {state.inventory}, Ready Harvests: {len(state.ready_harvests)}", flush=True)

    candidates = ActionPlanner.generate_market_candidates(state)
    print(f"Generated {len(candidates)} candidates: {candidates}", flush=True)

    eval_tuples = []
    for cand in candidates:
        is_safe, safety_reason = ActionSafetyGate.is_action_safe(cand, state)
        cand_score = ActionEvaluator.score_market_candidate(cand, state)
        approved, total_ucb, reason = CounterfactualSimulator.evaluate_exploration_candidate(
            cand, state, expert_score=100.0, confidence_threshold=0.20
        )
        print(f"Cand: {cand} | Safe: {is_safe} ({safety_reason}) | Score: {cand_score:.1f} | UCB: {total_ucb:.1f} | Approved: {approved} ({reason})", flush=True)
        if approved:
            eval_tuples.append((total_ucb, cand, reason))

    chosen = _POLICY.divergence_controller.select_controlled_deviation(eval_tuples, state)
    print(f"Chosen Deviation: {chosen.action_key if chosen else None} (Quality Score: {chosen.quality_rank_score if chosen else 0.0})", flush=True)

if __name__ == "__main__":
    trace_turn_100()
