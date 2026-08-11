"""APEX 3.0 Phase 4: State-Space Disagreement & Multi-Window Divergence Tournament.
Evaluates candidate approval/score disagreements between Static MCV (APEX 2.5-G) and Empirical MCV (APEX 3.0)
across multi-step decision windows (Steps 100-600) and multi-commodity action spaces.
"""

from __future__ import annotations
import sys
import os
import importlib.util
from typing import Dict, List, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.world_model import WorldState
from apex.expert import LPlusExpert
from apex.planner import ActionPlanner
from apex.counterfactual import CounterfactualSimulator
from apex.marginal_evaluator import MarginalActionEvaluator
from apex.empirical_mcv_evaluator import EmpiricalMarginalEvaluator

def load_opp_agent():
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("opp_mod", opp_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

opp_agent = load_opp_agent()
expert = LPlusExpert()

TEST_SEEDS = [
    590244349, 855978439, 1745977583, 91286593,
    1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008
]

EVAL_STEPS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

def run_state_space_disagreement_analysis():
    print("====================================================================================================", flush=True)
    print("🧪 APEX 3.0 PHASE 4: STATE-SPACE DISAGREEMENT & MULTI-WINDOW DIVERGENCE TOURNAMENT", flush=True)
    print("====================================================================================================", flush=True)

    agreements = 0
    disagreements = 0
    disagreement_details = []

    for seed_idx, seed in enumerate(TEST_SEEDS, start=1):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer = env.train([None, opp_agent])
        obs = trainer.reset()

        for step in range(720):
            wstate = WorldState(obs)
            expert_act = expert.decide(obs)

            if step in EVAL_STEPS:
                candidates = ActionPlanner.generate_market_candidates(wstate, expert_act)

                # 1. Evaluate via Static MCV (APEX 2.5-G)
                static_approved = []
                for cand in candidates:
                    app, sc, reas = CounterfactualSimulator.evaluate_exploration_candidate(
                        cand, expert_act, wstate, confidence_threshold=0.10, evaluator_cls=MarginalActionEvaluator
                    )
                    if app:
                        static_approved.append((sc, cand))
                static_approved.sort(key=lambda x: x[0], reverse=True)
                top_static = static_approved[0] if static_approved else None

                # 2. Evaluate via Empirical MCV (APEX 3.0)
                empirical_approved = []
                for cand in candidates:
                    app, sc, reas = CounterfactualSimulator.evaluate_exploration_candidate(
                        cand, expert_act, wstate, confidence_threshold=0.10, evaluator_cls=EmpiricalMarginalEvaluator
                    )
                    if app:
                        empirical_approved.append((sc, cand))
                empirical_approved.sort(key=lambda x: x[0], reverse=True)
                top_empirical = empirical_approved[0] if empirical_approved else None

                # 3. Check Disagreement
                static_act_key = str(top_static[1][0]) if top_static else "NONE"
                empirical_act_key = str(top_empirical[1][0]) if top_empirical else "NONE"

                if static_act_key == empirical_act_key:
                    agreements += 1
                else:
                    disagreements += 1
                    disagreement_details.append({
                        "seed": seed,
                        "step": step,
                        "cash": wstate.money,
                        "total_inv": sum(wstate.inventory.values()),
                        "candidates_count": len(candidates),
                        "static_choice": static_act_key,
                        "static_score": top_static[0] if top_static else 0.0,
                        "empirical_choice": empirical_act_key,
                        "empirical_score": top_empirical[0] if top_empirical else 0.0,
                    })

            obs, reward, done, info = trainer.step(expert_act)
            if done:
                break

    print("\n====================================================================================================", flush=True)
    print("📊 STATE-SPACE DISAGREEMENT SUMMARY REPORT", flush=True)
    print("====================================================================================================", flush=True)
    total_probed = agreements + disagreements
    print(f"Total State-Action Decision Probes   : {total_probed}")
    print(f"  ├── Agreements (Identical Choice)  : {agreements} ({agreements/max(1, total_probed)*100.0:.1f}%)")
    print(f"  └── Disagreements (Different Choice): {disagreements} ({disagreements/max(1, total_probed)*100.0:.1f}%)")
    print("----------------------------------------------------------------------------------------------------")

    if disagreement_details:
        print("\n--- 🔍 DISAGREEMENT SPOTLIGHT (STATIC VS EMPIRICAL CHOICE) ---", flush=True)
        for detail in disagreement_details[:15]:
            print(f"Seed: {detail['seed']} | Step: {detail['step']:3d} | Cash: ${detail['cash']:6.2f} | Static: {detail['static_choice']:<22} (Score {detail['static_score']:.2f}) | Empirical: {detail['empirical_choice']:<22} (Score {detail['empirical_score']:.2f})", flush=True)
    else:
        print("No disagreements found across evaluated decision windows.")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_state_space_disagreement_analysis()
