"""APEX 2.0 vs L+ 4.1 Head-to-Head Replay Evaluation Tournament.
"""

from __future__ import annotations
import sys
import os

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

def get_farm_inventory(farm_dict: dict) -> dict:
    return dict(farm_dict.get("inventory", {}) or {}) if isinstance(farm_dict, dict) else {}

def run_tournament():
    print("====================================================================================================")
    print("🏆 APEX 2.0 vs L+ 4.1 CONTROL: HEAD-TO-HEAD REPLAY TOURNAMENT EVALUATION")
    print("====================================================================================================")

    ctrl_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_l_plus.py")
    apex_path = os.path.join(BASE_DIR, "apex", "agent.py")
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")

    control_agent = load_agent(ctrl_path, "ctrl_agent")
    apex_agent = load_agent(apex_path, "apex_agent")
    opp_agent = load_agent(opp_path, "opp_agent")

    results = []

    for seed in SEEDS:
        print(f"\n🎮 Running Match on Seed: {seed}...")
        
        # 1. Run L+ 4.1 Control
        env_ctrl = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_ctrl.run([control_agent, opp_agent])
        
        steps_ctrl = env_ctrl.steps
        last_ctrl = steps_ctrl[-1]
        ctrl_farm = last_ctrl[0]["observation"]["farms"][0]
        ctrl_wealth = float(ctrl_farm.get("money", 0.0))
        ctrl_inv = sum(get_farm_inventory(ctrl_farm).values())

        # Count control action metrics
        ctrl_sells = 0
        ctrl_harvests = 0
        ctrl_last_sell = 0
        for idx, s in enumerate(steps_ctrl):
            act = s[0].get("action", {})
            if isinstance(act, dict):
                market = act.get("market", [])
                for ord in market:
                    if isinstance(ord, list) and len(ord) >= 1 and ord[0] == "SELL":
                        ctrl_sells += 1
                        ctrl_last_sell = idx
                hands = act.get("hands", [])
                for h in hands:
                    if isinstance(h, list) and len(h) >= 1 and h[0] == "HARVEST":
                        ctrl_harvests += 1

        # 2. Run APEX 2.0 Agent
        env_apex = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env_apex.run([apex_agent, opp_agent])

        steps_apex = env_apex.steps
        last_apex = steps_apex[-1]
        apex_farm = last_apex[0]["observation"]["farms"][0]
        apex_wealth = float(apex_farm.get("money", 0.0))
        apex_inv = sum(get_farm_inventory(apex_farm).values())

        apex_sells = 0
        apex_harvests = 0
        apex_last_sell = 0
        for idx, s in enumerate(steps_apex):
            act = s[0].get("action", {})
            if isinstance(act, dict):
                market = act.get("market", [])
                for ord in market:
                    if isinstance(ord, list) and len(ord) >= 1 and ord[0] == "SELL":
                        apex_sells += 1
                        apex_last_sell = idx
                hands = act.get("hands", [])
                for h in hands:
                    if isinstance(h, list) and len(h) >= 1 and h[0] == "HARVEST":
                        apex_harvests += 1

        margin = apex_wealth - ctrl_wealth
        win_status = "WIN ✅" if margin >= 0 else "LOSS ❌"

        res = {
            "seed": seed,
            "ctrl_wealth": ctrl_wealth,
            "apex_wealth": apex_wealth,
            "net_margin": margin,
            "win_status": win_status,
            "ctrl_last_sell": ctrl_last_sell,
            "apex_last_sell": apex_last_sell,
            "ctrl_harvests": ctrl_harvests,
            "apex_harvests": apex_harvests,
            "ctrl_sells": ctrl_sells,
            "apex_sells": apex_sells,
            "ctrl_term_inv": ctrl_inv,
            "apex_term_inv": apex_inv,
        }
        results.append(res)

        print(f"   L+ Control Wealth: ${ctrl_wealth:,.2f} | APEX 2.0 Wealth: ${apex_wealth:,.2f}")
        print(f"   Net Margin: ${margin:+,.2f} | Status: {win_status}")
        print(f"   Last Sell Step: L+ {ctrl_last_sell} vs APEX {apex_last_sell}")
        print(f"   Harvests: L+ {ctrl_harvests} vs APEX {apex_harvests} | Sells: L+ {ctrl_sells} vs APEX {apex_sells}")
        print(f"   Terminal Inventory: L+ {ctrl_inv} vs APEX {apex_inv}")

    # Summary Statistics
    avg_ctrl = sum(r["ctrl_wealth"] for r in results) / len(results)
    avg_apex = sum(r["apex_wealth"] for r in results) / len(results)
    avg_margin = avg_apex - avg_ctrl
    wins = sum(1 for r in results if r["net_margin"] >= 0)

    print("\n====================================================================================================")
    print("📊 TOURNAMENT EVALUATION SUMMARY")
    print("====================================================================================================")
    print(f"Total Matches: {len(results)} | APEX Wins: {wins}/{len(results)} ({wins/len(results)*100:.1f}%)")
    print(f"L+ 4.1 Avg Wealth  : ${avg_ctrl:,.2f}")
    print(f"APEX 2.0 Avg Wealth: ${avg_apex:,.2f}")
    print(f"Net Margin Delta   : ${avg_margin:+,.2f}")

    if wins >= 3 and avg_margin >= 0:
        print("🏆 GATE 1 & GATE 2 PASSED: APEX 2.0 AUTONOMOUS ADAPTATION IS VERIFIED & SUPREME!")
    else:
        print("⚠️ GATE FAIL: APEX 2.0 REQUIRES FURTHER POLICY DISAGREEMENT TUNING")

    print("====================================================================================================")

if __name__ == "__main__":
    run_tournament()
