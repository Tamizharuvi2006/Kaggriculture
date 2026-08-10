"""APEX 2.1 Multi-Tier Replay Tournament & Autonomous Divergence Harness.
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

def load_agent(filepath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def get_farm_inventory(farm_dict: dict) -> dict:
    return dict(farm_dict.get("inventory", {}) or {}) if isinstance(farm_dict, dict) else {}

def run_tier(tier_name: str, seeds: list):
    print(f"\n====================================================================================================")
    print(f"🎮 RUNNING TOURNAMENT EVALUATION FOR {tier_name} ({len(seeds)} SEEDS)")
    print("====================================================================================================")

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    control_agent = load_agent(ctrl_path, f"ctrl_{tier_name}")
    apex_agent = load_agent(apex_path, f"apex_{tier_name}")
    opp_agent = load_agent(opp_path, f"opp_{tier_name}")

    results = []

    for seed in seeds:
        # 1. Run L+ 4.1 Control
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([control_agent, opp_agent])
        ctrl_farm = env_ctrl.steps[-1][0]["observation"]["farms"][0]
        ctrl_wealth = float(ctrl_farm.get("money", 0.0))
        ctrl_inv = sum(get_farm_inventory(ctrl_farm).values())

        # 2. Run APEX 2.1 Agent
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_agent, opp_agent])
        apex_farm = env_apex.steps[-1][0]["observation"]["farms"][0]
        apex_wealth = float(apex_farm.get("money", 0.0))
        apex_inv = sum(get_farm_inventory(apex_farm).values())

        margin = apex_wealth - ctrl_wealth
        win_status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        res = {
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "net_margin": margin,
            "win_status": win_status,
            "ctrl_term_inv": ctrl_inv,
            "apex_term_inv": apex_inv,
        }
        results.append(res)

        print(f"Seed {seed:<10} | L+: ${ctrl_wealth:10,.2f} | APEX 2.1: ${apex_wealth:10,.2f} | Margin: ${margin:+10,.2f} | {win_status}")

    avg_ctrl = sum(r["ctrl_wealth"] for r in results) / len(results)
    avg_apex = sum(r["apex_wealth"] for r in results) / len(results)
    avg_margin = avg_apex - avg_ctrl
    wins = sum(1 for r in results if r["net_margin"] >= 0)

    print(f"\n📊 Summary for {tier_name}:")
    print(f"   Win Rate: {wins}/{len(results)} ({wins/len(results)*100:.1f}%)")
    print(f"   L+ 4.1 Avg Wealth  : ${avg_ctrl:,.2f}")
    print(f"   APEX 2.1 Avg Wealth: ${avg_apex:,.2f}")
    print(f"   Net Margin Delta   : ${avg_margin:+,.2f}")

    return {
        "tier": tier_name,
        "wins": wins,
        "total": len(results),
        "avg_ctrl": avg_ctrl,
        "avg_apex": avg_apex,
        "avg_margin": avg_margin
    }

def main():
    print("====================================================================================================")
    print("🚀 APEX 2.1 MULTI-TIER REPLAY TOURNAMENT & AUTONOMOUS DIVERGENCE AUDIT")
    print("====================================================================================================")

    res1 = run_tier("TIER 1 (FORENSIC SEEDS)", TIER1_FORENSIC_SEEDS)
    res2 = run_tier("TIER 2 (UNSEEN REPLAY SEEDS)", TIER2_UNSEEN_SEEDS)

    print("\n====================================================================================================")
    print("🏆 FINAL MULTI-TIER EVALUATION REPORT")
    print("====================================================================================================")
    print(f"Tier 1 (Forensic): Win Rate {res1['wins']}/{res1['total']} | Net Margin: ${res1['avg_margin']:+,.2f}")
    print(f"Tier 2 (Unseen)  : Win Rate {res2['wins']}/{res2['total']} | Net Margin: ${res2['avg_margin']:+,.2f}")
    print("====================================================================================================")

if __name__ == "__main__":
    main()
