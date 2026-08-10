"""Candidate L+ Final Sanity Check: Randomized Multi-Strategy Opponent Pool.

Runs 20 matches (Seeds 4000-4019) where opponent parameters (opening melons, cows, land timing, market orders)
are randomized per seed to verify that Candidate L+ generalizes across random opponent behaviors.
"""

import sys
import os
import json
import random
import importlib.util

if r"D:\kaggriculture" not in sys.path:
    sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
LPLUS_PATH = r"D:\kaggriculture\generalization_pipeline\submission_candidate_l_plus.py"


def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def create_randomized_opponent(seed):
    rng = random.Random(seed)
    mod = _load_mod(f"rand_opp_{seed}", V18_PATH)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "opening_melons": rng.choice([8, 10, 12, 15]),
        "cows": rng.choice([6, 8, 10, 12]),
        "v13_market_adaptation": rng.choice([True, False]),
        "land_ne_day": rng.choice([4, 5, 8, 10]),
        "strawberries": rng.choice([20, 34, 50]),
    })
    return mod.agent


def main():
    print("=" * 95, flush=True)
    print(" CANDIDATE L+ FINAL SANITY CHECK: RANDOMIZED MULTI-STRATEGY OPPONENTS", flush=True)
    print("=" * 95, flush=True)
    print(" Launching 20 Matches against Randomized Opponent Profiles (Seeds 4000-4019)...", flush=True)

    lplus_mod = _load_mod("lplus_mod_sanity", LPLUS_PATH)

    results = []
    lplus_wins = 0

    for seed in range(4000, 4020):
        opp_agent = create_randomized_opponent(seed)
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state = env.run([lplus_mod.agent, opp_agent])

        lplus_w = state[-1][0]["observation"]["farms"][0]["money"]
        opp_w = state[-1][1]["observation"]["farms"][1]["money"]
        won = lplus_w > opp_w
        if won:
            lplus_wins += 1

        margin = lplus_w - opp_w
        results.append({
            "seed": seed,
            "lplus_wealth": lplus_w,
            "opp_wealth": opp_w,
            "margin": margin,
            "won": won,
        })
        status_str = "WIN" if won else "LOSS"
        print(f" Seed {seed:4d} | L+: ${lplus_w:9.2f} | Opp: ${opp_w:9.2f} | Margin: +${margin:9.2f} | {status_str}", flush=True)

    total = len(results)
    win_rate = (lplus_wins / total) * 100.0
    avg_lplus = sum(r["lplus_wealth"] for r in results) / total
    avg_opp = sum(r["opp_wealth"] for r in results) / total
    avg_margin = sum(r["margin"] for r in results) / total
    min_lplus = min(r["lplus_wealth"] for r in results)

    print("\n" + "=" * 95, flush=True)
    print(" RANDOMIZED OPPONENT SANITY CHECK SUMMARY:", flush=True)
    print(f" - Candidate L+ Win Rate: {win_rate:.1f}% ({lplus_wins}/{total} Wins)", flush=True)
    print(f" - Candidate L+ Average Wealth: ${avg_lplus:.2f}", flush=True)
    print(f" - Randomized Opponent Average Wealth: ${avg_opp:.2f}", flush=True)
    print(f" - Average Victory Margin: +${avg_margin:.2f}", flush=True)
    print(f" - Minimum Floor Wealth: ${min_lplus:.2f}", flush=True)
    print("=" * 95, flush=True)

    output_path = r"D:\kaggriculture\generalization_pipeline\l_plus_randomized_sanity_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "total_matches": total,
            "win_rate": win_rate,
            "avg_lplus": avg_lplus,
            "avg_opp": avg_opp,
            "avg_margin": avg_margin,
            "min_floor": min_lplus,
            "raw_records": results,
        }, f, indent=2)

    print(f"Saved sanity check dataset to {output_path}", flush=True)


if __name__ == "__main__":
    main()
