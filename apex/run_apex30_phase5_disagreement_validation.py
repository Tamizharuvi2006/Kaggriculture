"""APEX 3.0 Phase 5: Counterfactual Disagreement Validation Engine.
Evaluates the 33 disagreement states between APEX 2.5-G (Static MCV) and APEX 3.0 (Empirical MCV).
Compares downstream match deltas and win rates when APEX 3.0 suppresses low-ROI deviations vs when APEX 2.5-G executes them.
"""

from __future__ import annotations
import sys
import os
import importlib.util
from typing import Dict, List, Any

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

def run_counterfactual_disagreement_validation():
    print("====================================================================================================", flush=True)
    print("🔥 APEX 3.0 PHASE 5: COUNTERFACTUAL DISAGREEMENT VALIDATION TOURNAMENT", flush=True)
    print("====================================================================================================", flush=True)

    disagreements = []

    # 1. Identify Disagreement Instances Across Matches
    for seed in TEST_SEEDS:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer = env.train([None, opp_agent])
        obs = trainer.reset()

        for step in range(720):
            wstate = WorldState(obs)
            expert_act = expert.decide(obs)

            if step in EVAL_STEPS:
                candidates = ActionPlanner.generate_market_candidates(wstate, expert_act)

                # Static MCV Choice
                static_app = []
                for cand in candidates:
                    app, sc, reas = CounterfactualSimulator.evaluate_exploration_candidate(
                        cand, expert_act, wstate, confidence_threshold=0.10, evaluator_cls=MarginalActionEvaluator
                    )
                    if app:
                        static_app.append((sc, cand))
                static_app.sort(key=lambda x: x[0], reverse=True)
                top_static = static_app[0] if static_app else None

                # Empirical MCV Choice
                emp_app = []
                for cand in candidates:
                    app, sc, reas = CounterfactualSimulator.evaluate_exploration_candidate(
                        cand, expert_act, wstate, confidence_threshold=0.10, evaluator_cls=EmpiricalMarginalEvaluator
                    )
                    if app:
                        emp_app.append((sc, cand))
                emp_app.sort(key=lambda x: x[0], reverse=True)
                top_emp = emp_app[0] if emp_app else None

                static_key = str(top_static[1][0]) if top_static else "NONE"
                emp_key = str(top_emp[1][0]) if top_emp else "NONE"

                if static_key != emp_key:
                    disagreements.append({
                        "seed": seed,
                        "step": step,
                        "cash": wstate.money,
                        "static_choice": top_static[1] if top_static else None,
                        "static_key": static_key,
                        "emp_choice": top_emp[1] if top_emp else None,
                        "emp_key": emp_key,
                    })

            obs, reward, done, info = trainer.step(expert_act)
            if done:
                break

    print(f"Identified {len(disagreements)} Disagreement States across test seeds.", flush=True)

    # 2. Run Counterfactual Validation for Disagreements
    print("\n--- 🧪 RUNNING COUNTERFACTUAL MATCH VALIDATION ---", flush=True)

    static_wins = 0
    empirical_wins = 0
    ties = 0

    accum_margin_diff = 0.0 # Empirical - Static

    validation_records = []

    for idx, dis in enumerate(disagreements, start=1):
        seed = dis["seed"]
        step = dis["step"]

        # Run Branch A: Static MCV Choice (Force Divergence)
        env_static = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer_static = env_static.train([None, opp_agent])
        obs_s = trainer_static.reset()

        for s in range(720):
            exp_s = expert.decide(obs_s)
            if s == step and dis["static_choice"]:
                # Execute static divergence
                act_to_do = dict(exp_s)
                alt_market = list(exp_s.get("market", [])) + dis["static_choice"]
                act_to_do["market"] = alt_market
            else:
                act_to_do = exp_s

            obs_s, rew, done_s, info_s = trainer_static.step(act_to_do)
            if done_s:
                break

        static_final_wealth = float(obs_s.get("farms", [{}])[0].get("money", 0.0))

        # Run Branch B: Empirical MCV Choice (Suppressed / Fallback to L+)
        env_emp = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer_emp = env_emp.train([None, opp_agent])
        obs_e = trainer_emp.reset()

        for s in range(720):
            exp_e = expert.decide(obs_e)
            if s == step and dis["emp_choice"]:
                act_to_do = dict(exp_e)
                alt_market = list(exp_e.get("market", [])) + dis["emp_choice"]
                act_to_do["market"] = alt_market
            else:
                act_to_do = exp_e

            obs_e, rew, done_e, info_e = trainer_emp.step(act_to_do)
            if done_e:
                break

        emp_final_wealth = float(obs_e.get("farms", [{}])[0].get("money", 0.0))

        diff = emp_final_wealth - static_final_wealth
        accum_margin_diff += diff

        if diff > 0:
            empirical_wins += 1
            status = "EMPIRICAL BETTER ✅"
        elif diff < 0:
            static_wins += 1
            status = "STATIC BETTER ❌"
        else:
            ties += 1
            status = "TIED EQUAL ➖"

        rec = {
            "seed": seed,
            "step": step,
            "cash": dis["cash"],
            "static_key": dis["static_key"],
            "emp_key": dis["emp_key"],
            "static_wealth": static_final_wealth,
            "emp_wealth": emp_final_wealth,
            "delta_diff": diff,
            "status": status
        }
        validation_records.append(rec)

        print(f"Disagreement {idx:2d}/{len(disagreements)} | Seed {seed} Step {step:3d} (Cash ${dis['cash']:6.2f}) | Static 2.5-G: ${static_final_wealth:,.2f} | Empirical 3.0: ${emp_final_wealth:,.2f} | Diff: ${diff:+,.2f} | {status}", flush=True)

    # 3. Final Summary Report
    print("\n====================================================================================================", flush=True)
    print("🏆 APEX 3.0 PHASE 5: DISAGREEMENT VALIDATION SUMMARY REPORT", flush=True)
    print("====================================================================================================", flush=True)
    print(f"Total Disagreements Evaluated       : {len(disagreements)}")
    print(f"  ├── Empirical 3.0 Superior (Saved $) : {empirical_wins} ({empirical_wins/max(1, len(disagreements))*100.0:.1f}%) 🏆")
    print(f"  ├── Static 2.5-G Superior           : {static_wins} ({static_wins/max(1, len(disagreements))*100.0:.1f}%)")
    print(f"  └── Equal Outcome (Tied)            : {ties} ({ties/max(1, len(disagreements))*100.0:.1f}%)")
    print("----------------------------------------------------------------------------------------------------")
    print(f"Net Cumulative Wealth Advantage (Empirical 3.0 - Static 2.5-G): ${accum_margin_diff:+,.2f}")
    print(f"Mean Wealth Advantage Per Disagreement                        : ${accum_margin_diff / max(1, len(disagreements)):+,.2f}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_counterfactual_disagreement_validation()
