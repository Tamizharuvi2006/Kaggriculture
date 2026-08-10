"""APEX 2.4-E Candidate Rejection Audit Benchmark Suite.
"""

from __future__ import annotations
import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

TIER1_FORENSIC_SEEDS = [590244349, 855978439, 1745977583, 91286593]
TIER2_UNSEEN_SEEDS = [1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008]

def load_agent_mod(filepath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_rejection_audit():
    print("====================================================================================================", flush=True)
    print("🔬 APEX 2.4-E CANDIDATE REJECTION TELEMETRY AUDIT BENCHMARK", flush=True)
    print("====================================================================================================", flush=True)

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    ctrl_mod = load_agent_mod(ctrl_path, "ctrl_mod")
    apex_mod = load_agent_mod(apex_path, "apex_mod")
    opp_mod = load_agent_mod(opp_path, "opp_mod")

    all_seeds = TIER1_FORENSIC_SEEDS + TIER2_UNSEEN_SEEDS
    results = []

    for seed in all_seeds:
        # Run Control Baseline
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([ctrl_mod.agent, opp_mod.agent])
        ctrl_wealth = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        # Run APEX 2.4-E Candidate
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_mod.agent, opp_mod.agent])
        apex_wealth = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        margin = apex_wealth - ctrl_wealth
        status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        res = {
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "net_margin": margin,
            "status": status
        }
        results.append(res)
        print(f"Seed {seed:<10} | L+: ${ctrl_wealth:10,.2f} | APEX 2.4-E: ${apex_wealth:10,.2f} | Margin: ${margin:+10,.2f} | {status}", flush=True)

    policy_inst = apex_mod._POLICY
    metrics = policy_inst.get_metrics()
    audit = metrics["rejection_audit"]

    print("\n====================================================================================================", flush=True)
    print("🏆 APEX 2.4-E CANDIDATE REJECTION AUDIT FINAL REPORT", flush=True)
    print("====================================================================================================", flush=True)
    print(f"Total Episode Decisions Evaluated : {metrics['total_decisions']}", flush=True)
    print(f"Total Candidate Actions Generated : {audit['total_generated']}", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"Candidates Passed Safety Gate (%) : {audit['passed_pct']:.2f}%", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print("REJECTION BREAKDOWN CATEGORIES:", flush=True)
    for cat, pct in audit["rejections"].items():
        print(f"  ├── {cat:<25}: {pct:6.2f}%", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"Expert Agreement Rate             : {metrics['agreement_rate_pct']:.2f}%", flush=True)
    print(f"Expert Divergence Rate            : {metrics['divergence_rate_pct']:.2f}%", flush=True)
    print(f"Captured Telemetry Traces         : {metrics['total_telemetry_traces']}", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_rejection_audit()
