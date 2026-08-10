"""Authoritative Candidate L+ Validation Tournament (Fast 4-Process Parallel Pool).

Evaluates Candidate L+ against 4 Diverse Opponent Archetypes across 100 TOTAL MATCHES on NEW UNSEEN SEEDS 2000-2024 (25 matches per archetype):
1. Capital Turtle (25 Matches: Seeds 2000-2024)
2. Cattle Rusher (25 Matches: Seeds 2000-2024)
3. Market Manipulator (25 Matches: Seeds 2000-2024)
4. Crop Expansionist (25 Matches: Seeds 2000-2024)

Tracks:
- Win Rate (%)
- Final Candidate Average Wealth ($)
- Final Opponent Average Wealth ($)
- Net Victory Margin ($)
- Worst-Case Floor ($)
- Catastrophic Losses Count (< $10,000)
"""

import sys
import os
import json
import statistics
import importlib.util
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
LPLUS_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"


def _run_single_match(args):
    archetype_name, seed = args

    spec_lp = importlib.util.spec_from_file_location(f"cand_lp400_{archetype_name}_{seed}", LPLUS_PATH)
    mod_lp = importlib.util.module_from_spec(spec_lp)
    spec_lp.loader.exec_module(mod_lp)
    agent_cand = mod_lp.agent

    spec_opp = importlib.util.spec_from_file_location(f"opp400_{archetype_name}_{seed}", V18_PATH)
    mod_opp = importlib.util.module_from_spec(spec_opp)
    spec_opp.loader.exec_module(mod_opp)

    if archetype_name == "Cattle_Rusher":
        mod_opp.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 12,
        })
        agent_opp = mod_opp.agent

    elif archetype_name == "Crop_Expansionist":
        mod_opp.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "strawberries_enabled": True,
            "cows": 6,
        })
        agent_opp = mod_opp.agent

    elif archetype_name == "Market_Manipulator":
        mod_opp.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        _base = mod_opp.agent

        def agent_manipulator(obs, configuration=None):
            action_dict = _base(obs)
            orders = action_dict.get("market", [])
            while len(orders) < 10:
                orders.append(['SELL', 'FERTILIZER', 1])
            action_dict["market"] = orders[:10]
            return action_dict

        agent_opp = agent_manipulator

    elif archetype_name == "Capital_Turtle":
        mod_opp.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 6,
        })
        agent_opp = mod_opp.agent
    else:
        agent_opp = mod_opp.agent

    p0_is_cand = (seed % 2 == 0)
    p0 = agent_cand if p0_is_cand else agent_opp
    p1 = agent_opp if p0_is_cand else agent_cand

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_cand = 0 if p0_is_cand else 1
    idx_opp = 1 if p0_is_cand else 0

    final_cand = float(state_history[-1][idx_cand]["observation"]["farms"][idx_cand]["money"])
    final_opp = float(state_history[-1][idx_opp]["observation"]["farms"][idx_opp]["money"])

    win = final_cand > final_opp

    return {
        "candidate": "Candidate_L+",
        "archetype": archetype_name,
        "seed": seed,
        "final_cand": final_cand,
        "final_opp": final_opp,
        "win": win,
        "margin": final_cand - final_opp,
    }


def main():
    print("=" * 95)
    print(" AUTHORITATIVE CANDIDATE L+ VALIDATION TOURNAMENT (4 PROCESS POOL)")
    print("=" * 95)

    archetypes = ["Capital_Turtle", "Cattle_Rusher", "Market_Manipulator", "Crop_Expansionist"]
    seeds = list(range(2000, 2025)) # 25 NEW UNSEEN SEEDS PER ARCHETYPE (100 TOTAL)

    tasks = [(arch, s) for arch in archetypes for s in seeds]

    workers = 4
    print(f" Launching 100 Matches across {workers} fast process workers...")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        match_results = list(executor.map(_run_single_match, tasks))

    summary = []
    for arch in archetypes:
        results = [r for r in match_results if r["archetype"] == arch]

        avg_cand = statistics.mean(r["final_cand"] for r in results)
        avg_opp = statistics.mean(r["final_opp"] for r in results)
        worst_floor = min(r["final_cand"] for r in results)
        catastrophic_losses = sum(1 for r in results if r["final_cand"] < 10000.0)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "candidate": "Candidate_L+",
            "archetype": arch,
            "matches": len(results),
            "win_rate": win_rate,
            "avg_cand": round(avg_cand, 2),
            "avg_opp": round(avg_opp, 2),
            "margin": round(avg_cand - avg_opp, 2),
            "worst_floor": round(worst_floor, 2),
            "catastrophic_losses": catastrophic_losses,
            "gate_pass": win_rate >= 60.0 and catastrophic_losses == 0,
        })

        status = "PASS (>60%)" if (win_rate >= 60.0 and catastrophic_losses == 0) else "FAIL"
        print(f" Opponent: {arch:<20} | L+ Avg: ${avg_cand:<10,.2f} | Opp Avg: ${avg_opp:<10,.2f} | Win Rate: {win_rate:.1f}% | Margin: +${avg_cand - avg_opp:<9,.2f} | Floor: ${worst_floor:<9,.2f} | Status: {status}")

    print("=" * 95)

    out_path = r"D:\kaggriculture\generalization_pipeline\authoritative_400_match_l_plus_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
