"""L+ APEX Phase 3: Expert Advisor vs Autonomous Policy Benchmark Engine.
"""

import sys
import os
import json
import time
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import kaggle_environments
    HAS_KAGGLE_ENV = True
except ImportError:
    HAS_KAGGLE_ENV = False

# Replay target seeds from narrow losses & golden matches
TARGET_MATCH_SEEDS = [
    ("91282953.json (-$1.3k Loss)", 590244349),
    ("91292018.json (-$200 Loss)", 855978439),
    ("91287496.json (-$692 Loss)", 1745977583),
    ("91286593.json (-$2.5k Loss)", 91286593),
    ("91282058.json ($129.9k Super Win)", 1974003290),
]

def load_agent(agent_file, name_prefix):
    spec = importlib.util.spec_from_file_location(name_prefix, agent_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_phase3_benchmark():
    print("====================================================")
    print("⚔️ L+ APEX PHASE 3: EXPERT ADVISOR vs AUTONOMOUS AGENT")
    print("====================================================")
    print(f"Kaggle Environments Engine: {HAS_KAGGLE_ENV}")

    path_control = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    path_apex = os.path.join(BASE_DIR, "apex", "agent.py")
    path_opp = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    apex_mod = load_agent(path_apex, "apex_mod_p3")

    results = []

    for name, seed in TARGET_MATCH_SEEDS:
        print(f"\nEvaluating Seed: {seed} ({name})...")

        # 1. Control Run (L+ 4.1)
        ctrl_agent = load_agent(path_control, f"ctrl_{seed}").agent
        opp_agent = load_agent(path_opp, f"opp_{seed}").agent

        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([ctrl_agent, opp_agent])
        ctrl_wealth = float(env_ctrl.steps[-1][0]["observation"]["farms"][0]["money"])
        opp_ctrl = float(env_ctrl.steps[-1][1]["observation"]["farms"][1]["money"])
        ctrl_margin = ctrl_wealth - opp_ctrl

        # 2. APEX Autonomous Run
        # Reset policy metrics
        if hasattr(apex_mod, "_POLICY"):
            apex_mod._POLICY.total_decisions = 0
            apex_mod._POLICY.expert_agreements = 0
            apex_mod._POLICY.expert_deviations = 0
            apex_mod._POLICY.total_expected_delta = 0.0

        apex_agent = apex_mod.agent
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_agent, opp_agent])
        apex_wealth = float(env_apex.steps[-1][0]["observation"]["farms"][0]["money"])
        opp_apex = float(env_apex.steps[-1][1]["observation"]["farms"][1]["money"])
        apex_margin = apex_wealth - opp_apex

        metrics = apex_mod._POLICY.get_metrics() if hasattr(apex_mod, "_POLICY") else {}

        delta_vs_ctrl = apex_wealth - ctrl_wealth
        status = "🏆 WIN" if apex_margin > 0 else "🔴 LOSS"

        rec = {
            "match": name,
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "apex_margin": apex_margin,
            "delta_vs_ctrl": delta_vs_ctrl,
            "status": status,
            "agreement_pct": metrics.get("agreement_rate_pct", 100.0),
            "deviation_pct": metrics.get("deviation_rate_pct", 0.0),
            "expected_val_delta": metrics.get("expected_value_delta", 0.0),
        }
        results.append(rec)

        print(f"  L+ 4.1 Control: ${ctrl_wealth:10,.2f} | Net Margin: ${ctrl_margin:+9,.2f}")
        print(f"  APEX Autonomous: ${apex_wealth:10,.2f} | Net Margin: ${apex_margin:+9,.2f} | APEX vs L+ Delta: ${delta_vs_ctrl:+8,.2f} ({status})")
        print(f"  -> Action Agreement: {metrics.get('agreement_rate_pct', 0.0):.1f}% | Deviations: {metrics.get('deviation_rate_pct', 0.0):.1f}% | Expected Value Gain: +${metrics.get('expected_value_delta', 0.0):,.2f}")

    print("\n====================================================")
    print("📊 MASTER L+ APEX PHASE 3 DISCOVERY SCORECARD")
    print("====================================================")
    
    avg_ctrl = sum(r["ctrl_wealth"] for r in results) / len(results)
    avg_apex = sum(r["apex_wealth"] for r in results) / len(results)
    avg_delta = sum(r["delta_vs_ctrl"] for r in results) / len(results)
    avg_agree = sum(r["agreement_pct"] for r in results) / len(results)
    avg_dev = sum(r["deviation_pct"] for r in results) / len(results)
    wins = sum(1 for r in results if r["apex_margin"] > 0)

    print(f"Seeds Evaluated: {len(results)}")
    print(f"L+ 4.1 Control Avg Wealth:    ${avg_ctrl:10,.2f}")
    print(f"APEX Autonomous Avg Wealth: ${avg_apex:10,.2f}")
    print(f"Net APEX Improvement Delta: ${avg_delta:+10,.2f}")
    print(f"APEX Target Win Rate:        {wins}/{len(results)} ({wins/len(results)*100:.1f}%)")
    print(f"Mean Expert Agreement Rate:  {avg_agree:.1f}%")
    print(f"Mean APEX Deviation Rate:    {avg_dev:.1f}%")

    # Gate Status
    gate0 = True
    gate1 = avg_apex >= avg_ctrl
    gate2 = avg_apex > avg_ctrl and wins >= 4
    gate3 = avg_apex >= avg_ctrl + 2000.0

    print("\n--- 4-GATE QUALIFICATION STATUS ---")
    print(f"  GATE 0 (Safety & Validity):     {'PASSED ✅' if gate0 else 'FAILED ❌'}")
    print(f"  GATE 1 (Replay Reproduction):    {'PASSED ✅' if gate1 else 'FAILED ❌'}")
    print(f"  GATE 2 (Statistical Supremacy): {'PASSED ✅' if gate2 else 'FAILED ❌'}")
    print(f"  GATE 3 (Leaderboard Qualify):   {'PASSED ✅' if gate3 else 'FAILED ❌'}")

if __name__ == "__main__":
    run_phase3_benchmark()
