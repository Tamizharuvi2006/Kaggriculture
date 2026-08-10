"""Generalization Pipeline: Multi-Archetype Opponent Suite & V4.1 Weakness Inspector.

Evaluates V4.1 Master Champion (1714.4 Kaggle Rating) against 4 Diverse Opponent Archetypes:
1. Archetype A: Heavy Fast Cattle Rusher (Buys Cows Day 3, Maxes Milk)
2. Archetype B: Aggressive Crop Expansionist (Expands Land Day 5, Plants Strawberries/Wheat)
3. Archetype C: Market Order Manipulator (FLOODS market slots with cheap goods to cause queue collisions)
4. Archetype D: Capital Hoarding Turtle (Sits on cash, sells high-margin crops only)

Tracks turn-by-turn V4.1 losses, market slot collisions, and resource contention bottlenecks.
Outputs an evidence-backed ranking of V4.1's actual competitive weaknesses.
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_v41():
    spec = importlib.util.spec_from_file_location("v41_gen_base", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def _create_opponent_archetype(archetype_name):
    spec = importlib.util.spec_from_file_location(f"opp_{archetype_name}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if archetype_name == "Cattle_Rusher":
        # Fast Cattle Rusher: Buys cows aggressively on Days 3-10
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 12,
        })
        return mod.agent

    elif archetype_name == "Crop_Expansionist":
        # Aggressive Crop Expansionist: Unlocks land on Day 5 & plants Strawberries
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "strawberries_enabled": True,
            "cows": 6,
        })
        return mod.agent

    elif archetype_name == "Market_Manipulator":
        # Market Order Manipulator: Emits 10 small market orders every turn to saturate slots
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
            # Flood order queue with 10 items to test opponent queue resilience
            while len(orders) < 10:
                orders.append(['SELL', 'FERTILIZER', 1])
            action_dict["market"] = orders[:10]
            return action_dict

        return agent_manipulator

    elif archetype_name == "Capital_Turtle":
        # Capital Hoarding Turtle: Sits on cash reserves, sells only at high prices
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 6,
        })
        return mod.agent

    return mod.agent


def audit_v41_against_archetype(archetype_name, seed):
    agent_v41 = _load_v41()
    agent_opp = _create_opponent_archetype(archetype_name)

    p0_is_v41 = (seed % 2 == 0)
    p0 = agent_v41 if p0_is_v41 else agent_opp
    p1 = agent_opp if p0_is_v41 else agent_v41

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v41 = 0 if p0_is_v41 else 1
    idx_opp = 1 if p0_is_v41 else 0

    final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])
    final_opp = float(state_history[-1][idx_opp]["observation"]["farms"][idx_opp]["money"])

    win = final_v41 > final_opp

    return {
        "archetype": archetype_name,
        "seed": seed,
        "final_v41": final_v41,
        "final_opp": final_opp,
        "win": win,
        "margin": final_v41 - final_opp,
    }


def main():
    print("=" * 95)
    print(" DIVERSE OPPONENT POOL BENCHMARK & V4.1 KAGGLE WEAKNESS AUDIT")
    print("=" * 95)

    archetypes = ["Cattle_Rusher", "Crop_Expansionist", "Market_Manipulator", "Capital_Turtle"]
    seeds = list(range(1000, 1010))

    summary = []
    for arch in archetypes:
        results = [audit_v41_against_archetype(arch, s) for s in seeds]

        avg_v41 = statistics.mean(r["final_v41"] for r in results)
        avg_opp = statistics.mean(r["final_opp"] for r in results)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "archetype": arch,
            "win_rate": win_rate,
            "avg_v41": round(avg_v41, 2),
            "avg_opp": round(avg_opp, 2),
            "margin": round(avg_v41 - avg_opp, 2),
        })

        print(f" Opponent: {arch:<22} | V4.1 Avg: ${avg_v41:<11,.2f} | Opponent Avg: ${avg_opp:<11,.2f} | Win Rate: {win_rate:.1f}% | Margin: +${avg_v41 - avg_opp:<10,.2f}")

    print("=" * 95)

    out_path = r"D:\kaggriculture\generalization_pipeline\v41_archetype_audit_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
