"""APEX 2.5-E: 12-Seed Prediction Calibration Audit & Value Calibration Report.
Compares Evaluator Predicted Advantage vs Realized Match Wealth Delta.
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
from apex.agent import agent as apex_agent, _POLICY

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

def run_calibration_audit():
    print("====================================================================================================", flush=True)
    print("🔬 APEX 2.5-E: 12-SEED PREDICTION CALIBRATION AUDIT", flush=True)
    print("====================================================================================================", flush=True)

    audit_records = []

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
            pred = trace.predicted_delta
            err = margin_delta - pred
            record = {
                "seed": seed,
                "step": trace.step,
                "action": trace.action_key,
                "regime": trace.state_signature.split("_")[-1] if "_" in trace.state_signature else "BALANCED",
                "predicted": pred,
                "actual": margin_delta,
                "error": err,
                "ctrl_wealth": ctrl_wealth,
                "apex_wealth": apex_wealth
            }
            audit_records.append(record)
            print(f"Seed {seed:10d} (Match {seed_idx:2d}/12) | Step {trace.step:3d} | Action: {trace.action_key:<20} | Pred: {pred:7.2f} | Actual: {margin_delta:+7.2f} | Err: {err:+7.2f}", flush=True)
        else:
            print(f"Seed {seed:10d} (Match {seed_idx:2d}/12) | No Divergence Executed (100% L+ match)", flush=True)

    # Compute Calibration Metrics
    print("\n====================================================================================================", flush=True)
    print("📊 PREDICTION CALIBRATION MATRIX & STATISTICAL AUDIT", flush=True)
    print("====================================================================================================", flush=True)

    if not audit_records:
        print("No divergence records collected.", flush=True)
        return

    n = len(audit_records)
    preds = [r["predicted"] for r in audit_records]
    actuals = [r["actual"] for r in audit_records]
    errors = [r["error"] for r in audit_records]

    mae = sum(abs(e) for e in errors) / n
    bias = sum(errors) / n

    mean_p = sum(preds) / n
    mean_a = sum(actuals) / n
    num = sum((p - mean_p) * (a - mean_a) for p, a in zip(preds, actuals))
    den = math.sqrt(sum((p - mean_p) ** 2 for p in preds) * sum((a - mean_a) ** 2 for a in actuals))
    corr = (num / den) if den > 1e-6 else 0.0

    pos = sum(1 for r in audit_records if r["actual"] > 0)
    neu = sum(1 for r in audit_records if r["actual"] == 0)
    neg = sum(1 for r in audit_records if r["actual"] < 0)

    print(f"Total Controlled Divergences Captured : {n}/12 Matches")
    print(f"Mean Predicted Advantage              : ${mean_p:8.2f}")
    print(f"Mean Realized Match Delta             : ${mean_a:+8.2f}")
    print("----------------------------------------------------------------------------------------------------")
    print(f"Mean Absolute Prediction Error (MAE)  : ${mae:8.2f}")
    print(f"Prediction Bias (Mean Over/Under Est) : ${bias:+8.2f} ({'OVERESTIMATION' if bias < 0 else 'UNDERESTIMATION'})")
    print(f"Pearson Correlation (r_pred,actual)   : {corr:+8.3f}")
    print("----------------------------------------------------------------------------------------------------")
    print(f"Positive Divergence Outcomes          : {pos} ({pos/n*100.0:.1f}%)")
    print(f"Neutral Divergence Outcomes           : {neu} ({neu/n*100.0:.1f}%)")
    print(f"Negative Divergence Outcomes (Loss)   : {neg} ({neg/n*100.0:.1f}%)")
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_calibration_audit()
