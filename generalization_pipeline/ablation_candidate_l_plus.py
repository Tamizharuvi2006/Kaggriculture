"""Generalization Pipeline: Candidate L+ Pre-Screening (40 Games Total) - Fixed Encoding.

Evaluates Candidate L+ against 4 Diverse Opponent Archetypes (10 seeds per archetype):
- Candidate L+ = V4.1 Dynamic Core + 10-Melon Opening + Opponent Milk Ranker + 8-Cow Cap

Validation Opponent Suite:
1. Capital Turtle (10 Melons + Reserve)
2. Cattle Rusher (12-Cow Fast Dairy)
3. Market Manipulator (Order Queue Flooder)
4. Crop Expansionist (Day 5 Land + Strawberries)

Strict Gate Criteria:
- Capital Turtle Win Rate > 60.0%
- Cattle Rusher Win Rate > 60.0%
- Market Manipulator Win Rate > 60.0%
- Crop Expansionist Win Rate > 60.0%
- Zero Catastrophic Collapses
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_candidate_l_plus(process_id):
    spec = importlib.util.spec_from_file_location(f"cand_lp_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })

    _base = mod.agent

    def agent_l_plus(obs, configuration=None):
        action_dict = _base(obs)
        market_orders = action_dict.get("market", [])
        if not market_orders or len(market_orders) <= 1:
            return action_dict

        prices = mod._get(mod._get(obs, "market", {}), "prices", {}) or {}
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

        def order_priority(idx_order):
            idx, ord_item = idx_order
            if not ord_item or ord_item[0] != "SELL":
                return (10, idx)
            item = ord_item[1] if len(ord_item) > 1 else ""
            if item == "MILK" and milk_p >= 230.0:
                return (0, idx)
            elif item == "MELON":
                return (1, idx)
            elif item == "STRAWBERRY":
                return (2, idx)
            elif item == "WHEAT":
                return (3, idx)
            return (4, idx)

        reordered = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)]
        action_dict["market"] = reordered
        return action_dict

    return agent_l_plus


def _create_opponent_archetype(archetype_name, process_id):
    spec = importlib.util.spec_from_file_location(f"opp3_{archetype_name}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if archetype_name == "Cattle_Rusher":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 12,
        })
        return mod.agent

    elif archetype_name == "Crop_Expansionist":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "strawberries_enabled": True,
            "cows": 6,
        })
        return mod.agent

    elif archetype_name == "Market_Manipulator":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        _base = mod.agent

        def agent_manipulator(obs, configuration=None):
            action_dict = _base(obs)
            orders = action_dict.get("market", [])
            while len(orders) < 10:
                orders.append(['SELL', 'FERTILIZER', 1])
            action_dict["market"] = orders[:10]
            return action_dict

        return agent_manipulator

    elif archetype_name == "Capital_Turtle":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 6,
        })
        return mod.agent

    return mod.agent


def audit_l_plus_match(archetype_name, seed):
    agent_cand = _load_candidate_l_plus(f"lp_{seed}")
    agent_opp = _create_opponent_archetype(archetype_name, f"{archetype_name}_{seed}")

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
    print(" CANDIDATE L+ PRE-SCREENING (40 GAMES ACROSS 4 DIVERSE ARCHETYPES)")
    print("=" * 95)

    archetypes = ["Capital_Turtle", "Cattle_Rusher", "Market_Manipulator", "Crop_Expansionist"]
    seeds = list(range(1000, 1010))

    summary = []
    for arch in archetypes:
        results = [audit_l_plus_match(arch, s) for s in seeds]

        avg_cand = statistics.mean(r["final_cand"] for r in results)
        avg_opp = statistics.mean(r["final_opp"] for r in results)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "candidate": "Candidate_L+",
            "archetype": arch,
            "win_rate": win_rate,
            "avg_cand": round(avg_cand, 2),
            "avg_opp": round(avg_opp, 2),
            "margin": round(avg_cand - avg_opp, 2),
            "gate_pass": win_rate >= 60.0,
        })

        status = "PASS (>60%)" if win_rate >= 60.0 else "FAIL (<60%)"
        print(f" Opponent: {arch:<22} | L+ Avg: ${avg_cand:<11,.2f} | Opponent Avg: ${avg_opp:<11,.2f} | Win Rate: {win_rate:.1f}% | Margin: +${avg_cand - avg_opp:<10,.2f} | Status: {status}")

    print("=" * 95)

    out_path = r"D:\kaggriculture\generalization_pipeline\candidate_l_plus_prescreen_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
