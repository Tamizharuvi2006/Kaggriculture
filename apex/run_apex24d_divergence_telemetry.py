"""APEX 2.4-D Zero-Cost Divergence & Telemetry Harness.
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

def run_telemetry_tier(tier_name: str, seeds: list):
    print(f"\n====================================================================================================", flush=True)
    print(f"📊 EVALUATING TELEMETRY FOR {tier_name} ({len(seeds)} SEEDS)", flush=True)
    print("====================================================================================================", flush=True)

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    ctrl_mod = load_agent_mod(ctrl_path, f"ctrl_{tier_name}")
    apex_mod = load_agent_mod(apex_path, f"apex_{tier_name}")
    opp_mod = load_agent_mod(opp_path, f"opp_{tier_name}")

    results = []

    for seed in seeds:
        # Run Control
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([ctrl_mod.agent, opp_mod.agent])
        ctrl_farm = env_ctrl.steps[-1][0]["observation"]["farms"][0]
        ctrl_wealth = float(ctrl_farm.get("money", 0.0))

        # Run APEX 2.4-D Candidate
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_mod.agent, opp_mod.agent])
        apex_farm = env_apex.steps[-1][0]["observation"]["farms"][0]
        apex_wealth = float(apex_farm.get("money", 0.0))

        margin = apex_wealth - ctrl_wealth
        status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        # Extract Telemetry Metrics directly from active agent policy instance
        policy_inst = apex_mod._POLICY
        metrics = policy_inst.get_metrics()
        policy_inst.record_match_outcome(margin)

        res = {
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "net_margin": margin,
            "win_status": status,
            "divergences": metrics["divergences"],
            "telemetry_traces": metrics["total_telemetry_traces"]
        }
        results.append(res)

        print(f"Seed {seed:<10} | L+: ${ctrl_wealth:10,.2f} | APEX 2.4-D: ${apex_wealth:10,.2f} | Margin: ${margin:+10,.2f} | {status} | Traces: {metrics['total_telemetry_traces']}", flush=True)

    avg_ctrl = sum(r["ctrl_wealth"] for r in results) / len(results)
    avg_apex = sum(r["apex_wealth"] for r in results) / len(results)
    avg_margin = avg_apex - avg_ctrl
    wins = sum(1 for r in results if r["net_margin"] >= 0)

    print(f"\n📊 Telemetry Summary for {tier_name}:", flush=True)
    print(f"   Win Rate           : {wins}/{len(results)} ({wins/len(results)*100:.1f}%)", flush=True)
    print(f"   L+ 4.1 Avg Wealth  : ${avg_ctrl:,.2f}", flush=True)
    print(f"   APEX 2.4-D Avg     : ${avg_apex:,.2f}", flush=True)
    print(f"   Net Margin Delta   : ${avg_margin:+,.2f}", flush=True)

    return {
        "tier": tier_name,
        "wins": wins,
        "total": len(results),
        "avg_ctrl": avg_ctrl,
        "avg_apex": avg_apex,
        "avg_margin": avg_margin,
        "policy_inst": apex_mod._POLICY
    }

def main():
    print("====================================================================================================", flush=True)
    print("🚀 APEX 2.4-D ZERO-COST SAFE DIVERGENCE & TELEMETRY BENCHMARK", flush=True)
    print("====================================================================================================", flush=True)

    res1 = run_telemetry_tier("TIER 1 (FORENSIC SEEDS)", TIER1_FORENSIC_SEEDS)
    res2 = run_telemetry_tier("TIER 2 (UNSEEN REPLAY SEEDS)", TIER2_UNSEEN_SEEDS)

    final_policy = res2["policy_inst"]
    final_metrics = final_policy.get_metrics()

    print("\n====================================================================================================", flush=True)
    print("🏆 FINAL EXHAUSTIVE DIVERGENCE TELEMETRY REPORT", flush=True)
    print("====================================================================================================", flush=True)
    print(f"Tier 1 (Forensic) Win Rate : {res1['wins']}/{res1['total']} | Net Margin: ${res1['avg_margin']:+,.2f}", flush=True)
    print(f"Tier 2 (Unseen) Win Rate   : {res2['wins']}/{res2['total']} | Net Margin: ${res2['avg_margin']:+,.2f}", flush=True)
    print("----------------------------------------------------------------------------------------------------", flush=True)
    print(f"Total Episode Decisions    : {final_metrics['total_decisions']}", flush=True)
    print(f"Expert Agreement Rate      : {final_metrics['agreement_rate_pct']:.2f}%", flush=True)
    print(f"Expert Divergence Rate     : {final_metrics['divergence_rate_pct']:.2f}%", flush=True)
    print(f"Captured Telemetry Traces  : {final_metrics['total_telemetry_traces']}", flush=True)
    print(f"Successful Divergences     : {final_metrics['successful_divergences']}", flush=True)
    print(f"Neutral Divergences        : {final_metrics['neutral_divergences']}", flush=True)
    print(f"Failed Divergences         : {final_metrics['failed_divergences']}", flush=True)
    print(f"Divergence Success Rate    : {final_metrics['divergence_success_rate_pct']:.2f}%", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    main()
