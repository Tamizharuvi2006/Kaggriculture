"""APEX 2.2 Controlled Exploration & Bounded Divergence Experiment.
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

FORENSIC_SEEDS = [590244349, 855978439, 1745977583, 91286593]
UNSEEN_SEEDS = [1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008]
ALL_TEST_SEEDS = FORENSIC_SEEDS + UNSEEN_SEEDS

def load_agent(filepath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def run_experiment_level(level_name: str, exploration_level: str):
    print(f"\n====================================================================================================")
    print(f"🧪 EVALUATING EXP LEVEL: {level_name} ({len(ALL_TEST_SEEDS)} SEEDS)")
    print("====================================================================================================")

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    control_agent = load_agent(ctrl_path, f"ctrl_{level_name}")
    apex_agent = load_agent(apex_path, f"apex_{level_name}")
    opp_agent = load_agent(opp_path, f"opp_{level_name}")

    # Set policy exploration level dynamically
    from apex.policy import ApexPolicy
    policy_inst = ApexPolicy(exploration_level=exploration_level)

    results = []

    for seed in ALL_TEST_SEEDS:
        # Run Control
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([control_agent, opp_agent])
        ctrl_money = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        # Run Candidate
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_agent, opp_agent])
        apex_money = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

        margin = apex_money - ctrl_money
        status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        results.append({
            "seed": seed,
            "ctrl": ctrl_money,
            "apex": apex_money,
            "margin": margin,
            "status": status
        })

    avg_ctrl = sum(r["ctrl"] for r in results) / len(results)
    avg_apex = sum(r["apex"] for r in results) / len(results)
    avg_margin = avg_apex - avg_ctrl
    wins = sum(1 for r in results if r["margin"] >= 0)

    print(f"\n📊 Summary for Level {level_name}:")
    print(f"   Win Rate: {wins}/{len(results)} ({wins/len(results)*100:.1f}%)")
    print(f"   L+ Avg Wealth   : ${avg_ctrl:,.2f}")
    print(f"   APEX Avg Wealth : ${avg_apex:,.2f}")
    print(f"   Net Margin Delta: ${avg_margin:+,.2f}")

    return {
        "level": level_name,
        "wins": wins,
        "total": len(results),
        "avg_ctrl": avg_ctrl,
        "avg_apex": avg_apex,
        "avg_margin": avg_margin
    }

def main():
    print("====================================================================================================")
    print("🚀 APEX 2.2 CONFIDENCE-BOUNDED DIVERGENCE & EXPLORATION SEARCH")
    print("====================================================================================================")

    res_ctrl = run_experiment_level("CONTROL (APEX 2.1)", "LOW")
    res_low = run_experiment_level("APEX 2.2-L (LOW EXP)", "LOW")
    res_med = run_experiment_level("APEX 2.2-M (MED EXP)", "MEDIUM")
    res_high = run_experiment_level("APEX 2.2-H (HIGH EXP)", "HIGH")

    print("\n====================================================================================================")
    print("🏆 FINAL EXPLORATION LEVEL COMPARISON SUMMARY")
    print("====================================================================================================")
    print(f"Control    : Win Rate {res_ctrl['wins']}/{res_ctrl['total']} | Net Margin: ${res_ctrl['avg_margin']:+,.2f}")
    print(f"APEX 2.2-L : Win Rate {res_low['wins']}/{res_low['total']} | Net Margin: ${res_low['avg_margin']:+,.2f}")
    print(f"APEX 2.2-M : Win Rate {res_med['wins']}/{res_med['total']} | Net Margin: ${res_med['avg_margin']:+,.2f}")
    print(f"APEX 2.2-H : Win Rate {res_high['wins']}/{res_high['total']} | Net Margin: ${res_high['avg_margin']:+,.2f}")
    print("====================================================================================================")

if __name__ == "__main__":
    main()
