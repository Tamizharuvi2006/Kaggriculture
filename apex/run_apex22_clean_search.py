"""APEX 2.2 Controlled Exploration & Bounded Divergence Clean Search.
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

SEEDS = [590244349, 855978439, 1745977583, 91286593]

def load_agent(filepath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def run_clean_search():
    print("====================================================================================================", flush=True)
    print("🚀 APEX 2.2 CONFIDENCE-BOUNDED DIVERGENCE & EXPLORATION SEARCH", flush=True)
    print("====================================================================================================", flush=True)

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    control_agent = load_agent(ctrl_path, "ctrl_agent")
    apex_agent = load_agent(apex_path, "apex_agent")
    opp_agent = load_agent(opp_path, "opp_agent")

    from apex.policy import ApexPolicy

    levels = ["LOW", "MEDIUM", "HIGH"]
    summary_reports = []

    for level in levels:
        print(f"\n🎮 Evaluating APEX 2.2 Level: {level}...", flush=True)
        # Re-instantiate policy exploration level
        ApexPolicy(exploration_level=level)

        level_results = []
        for seed in SEEDS:
            # Control run
            env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            env_ctrl.run([control_agent, opp_agent])
            ctrl_val = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

            # Candidate run
            env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            env_apex.run([apex_agent, opp_agent])
            apex_val = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

            margin = apex_val - ctrl_val
            status = "WIN ✅" if margin >= 0 else "LOSS ❌"
            level_results.append(margin)

            print(f"   Seed {seed:<10} | L+: ${ctrl_val:10,.2f} | APEX 2.2-{level[0]}: ${apex_val:10,.2f} | Margin: ${margin:+10,.2f} | {status}", flush=True)

        avg_margin = sum(level_results) / len(level_results)
        wins = sum(1 for m in level_results if m >= 0)
        summary_reports.append((level, wins, len(SEEDS), avg_margin))

    print("\n====================================================================================================", flush=True)
    print("🏆 APEX 2.2 CONFIDENCE-BOUNDED DIVERGENCE FINAL SUMMARY", flush=True)
    print("====================================================================================================", flush=True)
    for lvl, w, tot, avg_m in summary_reports:
        print(f"Level APEX 2.2-{lvl[0]} ({lvl:<6}): Win Rate {w}/{tot} ({w/tot*100:.1f}%) | Avg Net Margin Delta: ${avg_m:+10,.2f}", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    run_clean_search()
