"""Research 19: Single-Rule Ablation Experiment.

Measures the true end-to-end score impact of fine-tuning static target caps independently.

Evaluates 6 Single-Rule Ablation Variants across 10 official benchmark seeds (Seeds 1000-1009; 60 total matches):
- Baseline V8.1: cows = 12, strawberries = 30, opening_melons = 15
- Variant A: cows = 13, strawberries = 30
- Variant B: cows = 11, strawberries = 30
- Variant C: cows = 12, strawberries = 32
- Variant D: cows = 12, strawberries = 28
- Variant E: cows = 12, strawberries = 30, opening_melons = 18 (earlier/more melons)

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Idle Workers / Turn
- Empty Farmland Tiles / Turn
- Mid-Game Cash Floor (Day 15 / T360 Cash)
"""

import sys
import os
import json
import importlib.util
import statistics
import time

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_ablation", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}

VARIANTS = [
    {"label": "Baseline V8.1", "cows": 12, "strawberries": 30, "opening_melons": 15},
    {"label": "Variant A: Cows=13", "cows": 13, "strawberries": 30, "opening_melons": 15},
    {"label": "Variant B: Cows=11", "cows": 11, "strawberries": 30, "opening_melons": 15},
    {"label": "Variant C: Strawberries=32", "cows": 12, "strawberries": 32, "opening_melons": 15},
    {"label": "Variant D: Strawberries=28", "cows": 12, "strawberries": 28, "opening_melons": 15},
    {"label": "Variant E: Opening Melons=18", "cows": 12, "strawberries": 30, "opening_melons": 18},
]


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def run_single_rule_ablation(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 19: SINGLE-RULE ABLATION EXPERIMENT (10 Matches per Variant)")
    print("=" * 80)

    results = []

    for v_info in VARIANTS:
        label = v_info["label"]
        strat = dict(BASE_STRATEGY)
        strat["cows"] = v_info["cows"]
        strat["strawberries"] = v_info["strawberries"]
        strat["opening_melons"] = v_info["opening_melons"]

        print(f"\n--- Benchmarking {label} (Cows: {strat['cows']}, Strawberries: {strat['strawberries']}, Melons: {strat['opening_melons']}) ---")

        scores = []
        idle_worker_turns = []
        empty_tiles_list = []
        midgame_cash_list = []

        for seed in seeds:
            v18_mod.configure_strategy(dict(strat))

            match_idle = 0
            match_empty = 0
            t360_cash = 0.0

            def tracking_agent(obs):
                nonlocal match_idle, match_empty, t360_cash

                player = int(v18_mod._get(obs, "player", 0))
                farm = v18_mod._get(obs, "farms", [])[player]
                money = float(v18_mod._get(farm, "money", 0))
                day = int(v18_mod._get(obs, "day", 0))
                hour = int(v18_mod._get(obs, "hour", 0))
                step = day * 24 + hour

                if step == 360:
                    t360_cash = money

                tiles = v18_mod._get(farm, "tiles", [])
                unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

                empty_count = sum(
                    1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                    if v18_mod._active_target((x, y), day, unlocked) and tiles[y][x] is None
                )
                match_empty += empty_count

                action_dict = v18_mod.agent(obs)

                farmer_act = action_dict.get("farmer", ["PASS"])
                hands_acts = action_dict.get("hands", [])
                all_acts = [farmer_act] + hands_acts

                for act in all_acts:
                    if not act or act == ["PASS"]:
                        match_idle += 1

                return action_dict

            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            state = env.run([tracking_agent, _noop_agent])

            final_score = state[-1][0]["reward"]
            scores.append(final_score)
            idle_worker_turns.append(match_idle / 720.0)
            empty_tiles_list.append(match_empty / 720.0)
            midgame_cash_list.append(t360_cash)

        avg_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
        worst_score = min(scores)
        best_score = max(scores)

        avg_idle = statistics.mean(idle_worker_turns)
        avg_empty = statistics.mean(empty_tiles_list)
        avg_t360_cash = statistics.mean(midgame_cash_list)

        res = {
            "variant": label,
            "cows": strat["cows"],
            "strawberries": strat["strawberries"],
            "opening_melons": strat["opening_melons"],
            "avg_score": round(avg_score, 2),
            "median_score": round(median_score, 2),
            "worst_score": round(worst_score, 2),
            "best_score": round(best_score, 2),
            "std_dev": round(std_score, 2),
            "avg_idle_workers_per_turn": round(avg_idle, 2),
            "avg_empty_farmland_tiles": round(avg_empty, 2),
            "avg_t360_midgame_cash": round(avg_t360_cash, 2),
            "scores": scores,
        }

        results.append(res)
        print(f"  Avg Score: ${avg_score:,.2f} | Median: ${median_score:,.2f} | Worst: ${worst_score:,.2f} | StdDev: ${std_score:,.2f}")
        print(f"  Idle Workers: {avg_idle:.2f} | Empty Tiles: {avg_empty:.2f} | Day 15 Cash: ${avg_t360_cash:,.2f}")

    # Summary table
    print("\n" + "=" * 90)
    print(" RESEARCH 19: SINGLE-RULE ABLATION SUMMARY")
    print("=" * 90)
    print(f"{'Variant Label':<28} | {'Avg Score ($)':<13} | {'Median ($)':<11} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Idle W/Turn':<11}")
    print("-" * 95)
    for r in results:
        print(
            f"{r['variant']:<28} | ${r['avg_score']:<12,.2f} | ${r['median_score']:<10,.2f} | ${r['worst_score']:<9,.2f} | ${r['std_dev']:<8,.2f} | {r['avg_idle_workers_per_turn']:<11.2f}"
        )
    print("=" * 90)

    best_variant = max(results, key=lambda x: x["avg_score"])
    baseline_score = results[0]["avg_score"]
    gain = best_variant["avg_score"] - baseline_score

    print(f"\nBEST ABLATION VARIANT: {best_variant['variant']} with ${best_variant['avg_score']:,.2f} Avg Score (+${gain:,.2f} vs Baseline)!\n")

    report = {
        "results": results,
        "best_variant": best_variant,
        "baseline_score": baseline_score,
        "net_gain": round(gain, 2),
    }

    with open("research19_single_rule_ablation_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research19_single_rule_ablation_results.json")

    return report


if __name__ == "__main__":
    run_single_rule_ablation()
