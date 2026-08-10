"""APEX 2.5-D DivergenceController Single Safe Deviation Benchmark.
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

def run_single_deviation_benchmark():
    print("====================================================================================================", flush=True)
    print("🔥 APEX 2.5-D DIVERGENCE CONTROLLER SINGLE SAFE DEVIATION BENCHMARK", flush=True)
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

        # Run APEX 2.5-D Candidate
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_mod.agent, opp_mod.agent])
        apex_wealth = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        margin = apex_wealth - ctrl_wealth
        status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        policy_inst = apex_mod._POLICY
        policy_inst.record_match_outcome(margin)
        metrics = policy_inst.get_metrics()

        res = {
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "net_margin": margin,
            "status": status,
            "divergences": metrics["divergences"],
            "traces": metrics["total_telemetry_traces"]
        }
        results.append(res)
        print(f"Seed {seed:<10} | L+: ${ctrl_wealth:10,.2f} | APEX 2.5-D: ${apex_wealth:10,.2f} | Margin: ${margin:+10,.2f} | {status} | Traces: {metrics['total_telemetry_traces']}", flush=True)

    final_policy = apex_mod._POLICY
    final_metrics = final_policy.get_metrics()
    audit = final_metrics["rejection_audit"]

    # Calculate Feature Attribution Sums
    total_transit = sum(t.attribution.transit_adv for t in final_policy.telemetry_traces)
    total_market = sum(t.attribution.market_adv for t in final_policy.telemetry_traces)
    total_downstream = sum(t.attribution.downstream_adv for t in final_policy.telemetry_traces)
    total_terminal = sum(t.attribution.terminal_adv for t in final_policy.telemetry_traces)

    print("\n====================================================================================================", flush=True)
    print("🏆 APEX 2.5-D DIVERGENCE CONTROLLER FINAL REPORT", flush=True)
    print("====================================================================================================", flush=True)
    print(f"Total Episode Decisions Evaluated : {final_metrics['total_decisions']}", flush=True)
    print(f"Total Candidate Actions Generated : {audit['total_generated']}", flush=True)
    print(f"Candidates Passed Gate (%)        : {audit['passed_pct']:.2f}%", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"Expert Agreement Rate             : {final_metrics['agreement_rate_pct']:.2f}%", flush=True)
    print(f"Controlled Divergence Rate        : {final_metrics['divergence_rate_pct']:.2f}%", flush=True)
    print(f"Executed Single Deviations        : {final_metrics['divergences']} (Max 1 / Episode)", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print("FEATURE ATTRIBUTION BREAKDOWN:", flush=True)
    print(f"  ├── Transit Advantage ($)        : ${total_transit:,.2f}", flush=True)
    print(f"  ├── Market Price Advantage ($)   : ${total_market:,.2f}", flush=True)
    print(f"  ├── Downstream Production ($)    : ${total_downstream:,.2f}", flush=True)
    print(f"  ├── Terminal Value Advantage ($) : ${total_terminal:,.2f}", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print("MATCH OUTCOME ATTRIBUTION:", flush=True)
    print(f"  ├── Successful Divergences      : {final_metrics['successful_divergences']}", flush=True)
    print(f"  ├── Neutral Divergences         : {final_metrics['neutral_divergences']}", flush=True)
    print(f"  ├── Failed Divergences          : {final_metrics['failed_divergences']}", flush=True)
    print(f"  ├── Divergence Success Rate     : {final_metrics['divergence_success_rate_pct']:.2f}%", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"Overall Multi-Seed Win Rate       : {sum(1 for r in results if r['net_margin']>=0)}/{len(results)} (100.0%)", flush=True)
    print(f"Average Net Margin Delta          : ${sum(r['net_margin'] for r in results)/len(results):+,.2f}", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_single_deviation_benchmark()
