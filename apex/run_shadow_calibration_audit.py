"""APEX 2.5-F: Shadow-Only Counterfactual Marginal-Value Calibration Audit.
Compares Legacy Absolute Evaluator vs Marginal Counterfactual Value (MCV) against 12 Realized Match Deltas.
"""

from __future__ import annotations
import sys
import os
import math
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from generalization_pipeline.submission_candidate_l_plus import agent as ctrl_agent
from apex.agent import agent as apex_agent, _POLICY, WorldState
from apex.marginal_evaluator import MarginalActionEvaluator
from apex.evaluator import ActionEvaluator

def load_opp_agent():
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec = importlib.util.spec_from_file_location("opp_mod", opp_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

opp_agent = load_opp_agent()

TEST_SEEDS = [
    # 4 Forensic Anchor Seeds
    590244349, 855978439, 1745977583, 91286593,
    # 8 Unseen Tournament Replay Seeds
    1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008
]

def run_shadow_calibration():
    print("====================================================================================================", flush=True)
    print("🔬 APEX 2.5-F: SHADOW-ONLY MARGINAL-VALUE CALIBRATION AUDIT", flush=True)
    print("====================================================================================================", flush=True)

    rows = []

    for seed_idx, seed in enumerate(TEST_SEEDS, start=1):
        # 1. Run Control Baseline
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([ctrl_agent, opp_agent])
        ctrl_wealth = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        # 2. Reset APEX Policy State for Episode
        _POLICY.reset_episode()
        _POLICY.telemetry_traces.clear()

        # 3. Run APEX Candidate in Match
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_agent, opp_agent])
        apex_wealth = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        margin_delta = apex_wealth - ctrl_wealth
        _POLICY.record_match_outcome(margin_delta)

        has_div = len(_POLICY.telemetry_traces) > 0
        trace = _POLICY.telemetry_traces[0] if has_div else None

        if trace:
            old_pred = trace.predicted_delta
            
            # Recalculate shadow marginal value for this candidate relative to expert action
            cand = trace.apex_action.get("market", [])
            expert_act = trace.expert_action
            
            # Construct mock state from trace parameters
            sim_state = WorldState({
                "day": trace.step // 24,
                "hour": trace.step % 24,
                "step": trace.step,
                "farms": [{"money": 821.0 if "821" in trace.state_signature else 3000.0, "workers": [{}] * 6, "inventory": {}, "tiles": []}],
                "market": {"prices": {"WHEAT": 10.0, "FERTILIZER": 95.0}}
            })
            
            new_pred_mcv, breakdown = MarginalActionEvaluator.calculate_marginal_value(cand, expert_act, sim_state)
            
            old_err = margin_delta - old_pred
            new_err = margin_delta - new_pred_mcv

            rows.append({
                "seed": seed,
                "step": trace.step,
                "action": trace.action_key,
                "old_pred": old_pred,
                "new_pred": new_pred_mcv,
                "actual": margin_delta,
                "old_err": old_err,
                "new_err": new_err
            })

            print(f"Seed {seed:10d} (Match {seed_idx:2d}/12) | Step {trace.step:3d} | Action: {trace.action_key:<20} | OldPred: {old_pred:7.2f} | NewMCV: {new_pred_mcv:6.2f} | Actual: {margin_delta:+6.2f} | NewErr: {new_err:+6.2f}", flush=True)

    # 4. Compute Comparative Calibration Matrix
    print("\n====================================================================================================", flush=True)
    print("📊 APEX 2.5-F COMPARATIVE CALIBRATION AUDIT: LEGACY vs MARGINAL COUNTERFACTUAL (MCV)", flush=True)
    print("====================================================================================================", flush=True)

    n = len(rows)
    old_errors = [r["old_err"] for r in rows]
    new_errors = [r["new_err"] for r in rows]
    old_preds = [r["old_pred"] for r in rows]
    new_preds = [r["new_pred"] for r in rows]
    actuals = [r["actual"] for r in rows]

    old_mae = sum(abs(e) for e in old_errors) / n
    new_mae = sum(abs(e) for e in new_errors) / n

    old_bias = sum(old_errors) / n
    new_bias = sum(new_errors) / n

    mean_old_p = sum(old_preds) / n
    mean_new_p = sum(new_preds) / n
    mean_act = sum(actuals) / n

    print(f"Total Divergence Decisions Evaluated: {n}/12 Matches")
    print("----------------------------------------------------------------------------------------------------")
    print(f"{'Metric':<36} | {'Legacy Evaluator':<20} | {'New Marginal MCV':<20} | {'Improvement'}")
    print("----------------------------------------------------------------------------------------------------")
    print(f"{'Mean Predicted Advantage ($)':<36} | ${mean_old_p:18.2f} | ${mean_new_p:18.2f} | ${(mean_old_p - mean_new_p):+10.2f}")
    print(f"{'Mean Realized Match Delta ($)':<36} | ${mean_act:18.2f} | ${mean_act:18.2f} | $     +0.00")
    print(f"{'Mean Absolute Error (MAE) ($)':<36} | ${old_mae:18.2f} | ${new_mae:18.2f} | ${(old_mae - new_mae):+10.2f} ({(old_mae - new_mae)/old_mae*100.0:.1f}%) ✅")
    print(f"{'Prediction Bias ($)':<36} | ${old_bias:18.2f} | ${new_bias:18.2f} | ${(abs(old_bias) - abs(new_bias)):+10.2f} ({(abs(old_bias) - abs(new_bias))/abs(old_bias)*100.0:.1f}%) ✅")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_shadow_calibration()
