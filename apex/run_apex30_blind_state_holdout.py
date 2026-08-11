"""APEX 3.0: Blind State-Conditioned Holdout Experiment.
Probes 20 completely unseen random seeds across multi-step decision windows (Steps 100-600),
extracts unseen disagreement states between Static MCV (APEX 2.5-G) and Empirical MCV (APEX 3.0),
and performs counterfactual match validation without any hyperparameter tuning.
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

# 20 Completely Fresh Blind Seeds (Never used in tuning or previous validation)
BLIND_SEEDS = [
    888001, 888002, 888003, 888004, 888005, 888006, 888007, 888008, 888009, 888010,
    888011, 888012, 888013, 888014, 888015, 888016, 888017, 888018, 888019, 888020
]

EVAL_STEPS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

def run_blind_state_holdout():
    print("====================================================================================================", flush=True)
    print("🧪 APEX 3.0: BLIND STATE-CONDITIONED HOLDOUT EXPERIMENT (20 UNSEEN SEEDS)", flush=True)
    print("====================================================================================================", flush=True)

    unseen_disagreements = []

    # 1. Probing Decision Windows Across Unseen Seeds
    for seed in BLIND_SEEDS:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer = env.train([None, opp_agent])
        obs = trainer.reset()

        for step in range(720):
            wstate = WorldState(obs)
            expert_act = expert.decide(obs)

            if step in EVAL_STEPS:
                candidates = ActionPlanner.generate_market_candidates(wstate, expert_act)

                # Static MCV Choice (2.5-G)
                static_app = []
                for cand in candidates:
                    app, sc, reas = CounterfactualSimulator.evaluate_exploration_candidate(
                        cand, expert_act, wstate, confidence_threshold=0.10, evaluator_cls=MarginalActionEvaluator
                    )
                    if app:
                        static_app.append((sc, cand))
                static_app.sort(key=lambda x: x[0], reverse=True)
                top_static = static_app[0] if static_app else None

                # Empirical MCV Choice (3.0)
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
                    unseen_disagreements.append({
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

    print(f"Discovered {len(unseen_disagreements)} Unseen Disagreement States across 220 probed decision windows.", flush=True)

    # 2. Counterfactual Match Validation for Unseen Disagreements
    print("\n--- 🔬 COUNTERFACTUAL MATCH SIMULATION FOR UNSEEN DISAGREEMENTS ---", flush=True)

    emp_wins = 0
    static_wins = 0
    ties = 0
    accum_diff = 0.0

    for idx, dis in enumerate(unseen_disagreements, start=1):
        seed = dis["seed"]
        step = dis["step"]

        # Static 2.5-G Branch
        env_static = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        trainer_static = env_static.train([None, opp_agent])
        obs_s = trainer_static.reset()

        for s in range(720):
            exp_s = expert.decide(obs_s)
            if s == step and dis["static_choice"]:
                act_to_do = dict(exp_s)
                alt_market = list(exp_s.get("market", [])) + dis["static_choice"]
                act_to_do["market"] = alt_market
            else:
                act_to_do = exp_s
            obs_s, rew, done_s, info_s = trainer_static.step(act_to_do)
            if done_s:
                break

        static_wealth = float(obs_s.get("farms", [{}])[0].get("money", 0.0))

        # Empirical 3.0 Branch
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

        emp_wealth = float(obs_e.get("farms", [{}])[0].get("money", 0.0))

        diff = emp_wealth - static_wealth
        accum_diff += diff

        if diff > 0:
            emp_wins += 1
            status = "EMPIRICAL 3.0 BETTER ✅"
        elif diff < 0:
            static_wins += 1
            status = "STATIC 2.5-G BETTER ❌"
        else:
            ties += 1
            status = "TIED EQUAL ➖"

        print(f"Unseen Disagreement {idx:2d}/{len(unseen_disagreements)} | Seed {seed} Step {step:3d} (Cash ${dis['cash']:6.2f}) | Static: ${static_wealth:,.2f} | Empirical: ${emp_wealth:,.2f} | Diff: ${diff:+,.2f} | {status}", flush=True)

    # 3. Final Summary Report
    print("\n====================================================================================================", flush=True)
    print("🏆 APEX 3.0 BLIND STATE-CONDITIONED HOLDOUT SUMMARY REPORT", flush=True)
    print("====================================================================================================", flush=True)
    total_dis = len(unseen_disagreements)
    print(f"Total Unseen Disagreement States Tested : {total_dis}")
    print(f"  ├── Empirical 3.0 Superior (Saved Cash): {emp_wins} ({emp_wins/max(1, total_dis)*100.0:.1f}%) 🏆")
    print(f"  ├── Static 2.5-G Superior           : {static_wins} ({static_wins/max(1, total_dis)*100.0:.1f}%)")
    print(f"  └── Equal / Tied Outcome          : {ties} ({ties/max(1, total_dis)*100.0:.1f}%)")
    print("----------------------------------------------------------------------------------------------------")
    print(f"Net Cumulative Holdout Delta (Empirical 3.0 - 2.5G): ${accum_diff:+,.2f}")
    print(f"Mean Wealth Gain Per Unseen Disagreement State     : ${accum_diff / max(1, total_dis):+,.2f}")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_blind_state_holdout()
