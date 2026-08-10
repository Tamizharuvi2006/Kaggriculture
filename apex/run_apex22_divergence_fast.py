"""APEX 2.2 Parallel Exploration Level Search Benchmark.
"""

from __future__ import annotations
import sys
import os
import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
import importlib.util

FORENSIC_SEEDS = [590244349, 855978439, 1745977583, 91286593]
UNSEEN_SEEDS = [1001, 2002, 3003, 4004]  # 4 seeds for ultra-fast parallel validation
ALL_TEST_SEEDS = FORENSIC_SEEDS + UNSEEN_SEEDS

def load_agent(filepath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def run_single_seed_match(args):
    seed, level_name, exp_level = args
    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    control_agent = load_agent(ctrl_path, f"ctrl_{seed}_{exp_level}")
    apex_agent = load_agent(apex_path, f"apex_{seed}_{exp_level}")
    opp_agent = load_agent(opp_path, f"opp_{seed}_{exp_level}")

    # Set exploration level
    from apex.policy import ApexPolicy
    policy_inst = ApexPolicy(exploration_level=exp_level)

    # 1. Run Control
    env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_ctrl.run([control_agent, opp_agent])
    ctrl_money = float(env_ctrl.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

    # 2. Run Candidate
    env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_apex.run([apex_agent, opp_agent])
    apex_money = float(env_apex.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))

    margin = apex_money - ctrl_money
    status = "WIN ✅" if margin >= 0 else "LOSS ❌"

    return {
        "seed": seed,
        "ctrl": ctrl_money,
        "apex": apex_money,
        "margin": margin,
        "status": status
    }

def run_level_parallel(level_name: str, exp_level: str):
    print(f"\n🎮 Running {level_name} across {len(ALL_TEST_SEEDS)} seeds in parallel...", flush=True)
    tasks = [(seed, level_name, exp_level) for seed in ALL_TEST_SEEDS]
    
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for res in executor.map(run_single_seed_match, tasks):
            results.append(res)
            print(f"   Seed {res['seed']:<10} | L+: ${res['ctrl']:10,.2f} | APEX: ${res['apex']:10,.2f} | Margin: ${res['margin']:+10,.2f} | {res['status']}", flush=True)

    avg_ctrl = sum(r["ctrl"] for r in results) / len(results)
    avg_apex = sum(r["apex"] for r in results) / len(results)
    avg_margin = avg_apex - avg_ctrl
    wins = sum(1 for r in results if r["margin"] >= 0)

    print(f"\n📊 Summary for {level_name}: Win Rate {wins}/{len(results)} | Net Margin: ${avg_margin:+,.2f}", flush=True)
    return {
        "level": level_name,
        "wins": wins,
        "total": len(results),
        "avg_ctrl": avg_ctrl,
        "avg_apex": avg_apex,
        "avg_margin": avg_margin
    }

def main():
    print("====================================================================================================", flush=True)
    print("🚀 APEX 2.2 FAST PARALLEL EXPLORATION LEVEL SEARCH BENCHMARK", flush=True)
    print("====================================================================================================", flush=True)

    res_ctrl = run_level_parallel("CONTROL (APEX 2.1)", "LOW")
    res_low = run_level_parallel("APEX 2.2-L (LOW EXP)", "LOW")
    res_med = run_level_parallel("APEX 2.2-M (MED EXP)", "MEDIUM")
    res_high = run_level_parallel("APEX 2.2-H (HIGH EXP)", "HIGH")

    print("\n====================================================================================================", flush=True)
    print("🏆 FINAL PARALLEL EXPLORATION LEVEL COMPARISON SUMMARY", flush=True)
    print("====================================================================================================", flush=True)
    print(f"Control    : Win Rate {res_ctrl['wins']}/{res_ctrl['total']} | Net Margin: ${res_ctrl['avg_margin']:+,.2f}", flush=True)
    print(f"APEX 2.2-L : Win Rate {res_low['wins']}/{res_low['total']} | Net Margin: ${res_low['avg_margin']:+,.2f}", flush=True)
    print(f"APEX 2.2-M : Win Rate {res_med['wins']}/{res_med['total']} | Net Margin: ${res_med['avg_margin']:+,.2f}", flush=True)
    print(f"APEX 2.2-H : Win Rate {res_high['wins']}/{res_high['total']} | Net Margin: ${res_high['avg_margin']:+,.2f}", flush=True)
    print("====================================================================================================", flush=True)

if __name__ == "__main__":
    main()
