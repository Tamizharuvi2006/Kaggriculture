"""Generalization Pipeline: Dual-Candidate Pre-Screening (Candidate L vs Candidate C).

Evaluates 80 total games across 4 Diverse Opponent Archetypes (10 seeds per archetype per candidate):
1. Candidate L: Early Liquidity Response (10-Melon Opening + Pure V4.1 Core)
2. Candidate C: Dynamic Cattle-Rusher Response (15-Melon Opening + Conditional Cow #9-10 Expansion when Opponent Cows >= 8 and Cash >= $2.5k)

Opponent Archetypes:
- Capital Turtle
- Cattle Rusher
- Market Manipulator
- Crop Expansionist

Measures win rates & margins across all 4 archetypes simultaneously.
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_candidate(candidate_code, process_id):
    spec = importlib.util.spec_from_file_location(f"cand_{candidate_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if candidate_code == "Candidate_L":
        # Candidate L: 10-Melon Opening + Pure V4.1 Core (Ranker OFF)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
        return mod.agent

    elif candidate_code == "Candidate_C":
        # Candidate C: 15-Melon Opening + Conditional Cow #9-10 when Opponent Cows >= 8 and Cash >= $2.5k
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        _base = mod.agent

        def agent_c(obs, configuration=None):
            farm0 = obs["farms"][0]
            money = float(farm0["money"])
            cows = sum(1 for r in farm0["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")

            opp_farm = obs["farms"][1]
            opp_cows = sum(1 for r in opp_farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")

            # Conditional Cow #9-10 Trigger
            if opp_cows >= 8 and cows in (8, 9) and money >= 2500.0:
                action_dict = _base(obs)
                orders = action_dict.get("market", [])
                if not any(o[0] == "BUY_ANIMAL" and len(o) > 1 and o[1] == "COW" for o in orders):
                    action_dict["market"] = [['BUY_ANIMAL', 'COW', 1]] + orders
                    return action_dict

            return _base(obs)

        return agent_c


def _create_opponent_archetype(archetype_name, process_id):
    spec = importlib.util.spec_from_file_location(f"opp2_{archetype_name}_{process_id}", V18_PATH)
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


def audit_candidate_match(candidate_code, archetype_name, seed):
    agent_cand = _load_candidate(candidate_code, f"{candidate_code}_{seed}")
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
        "candidate": candidate_code,
        "archetype": archetype_name,
        "seed": seed,
        "final_cand": final_cand,
        "final_opp": final_opp,
        "win": win,
        "margin": final_cand - final_opp,
    }


def main():
    print("=" * 95)
    print(" DUAL-CANDIDATE PRE-SCREENING: CANDIDATE L VS CANDIDATE C (80 GAMES)")
    print("=" * 95)

    candidates = ["Candidate_L", "Candidate_C"]
    archetypes = ["Capital_Turtle", "Cattle_Rusher", "Market_Manipulator", "Crop_Expansionist"]
    seeds = list(range(1000, 1010))

    all_results = []
    for cand in candidates:
        print(f"\n --- EVALUATING {cand} ---")
        for arch in archetypes:
            results = [audit_candidate_match(cand, arch, s) for s in seeds]

            avg_cand = statistics.mean(r["final_cand"] for r in results)
            avg_opp = statistics.mean(r["final_opp"] for r in results)
            wins = sum(1 for r in results if r["win"])
            win_rate = (wins / len(results)) * 100.0

            all_results.append({
                "candidate": cand,
                "archetype": arch,
                "win_rate": win_rate,
                "avg_cand": round(avg_cand, 2),
                "avg_opp": round(avg_opp, 2),
                "margin": round(avg_cand - avg_opp, 2),
            })

            print(f" Opponent: {arch:<22} | {cand} Avg: ${avg_cand:<11,.2f} | Opponent Avg: ${avg_opp:<11,.2f} | Win Rate: {win_rate:.1f}% | Margin: +${avg_cand - avg_opp:<10,.2f}")

    print("=" * 95)

    out_path = r"D:\kaggriculture\generalization_pipeline\candidate_l_c_prescreen_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    main()
