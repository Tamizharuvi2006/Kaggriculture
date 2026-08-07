"""Research 16: Cow Replacement Frontier.

Evaluates the labor-efficiency & economic trade-off between Cows (steady liquidity) and Strawberries (high ROI).

Benchmarks 5 Cow configurations across 10 official seeds (Seeds 1000-1009):
1. 0 Cows  (0 Cows, 50 Strawberries max allocation)
2. 4 Cows  (4 Cows, 40 Strawberries)
3. 8 Cows  (8 Cows, 35 Strawberries)
4. 12 Cows (12 Cows, 30 Strawberries - Baseline V8.1)
5. 16 Cows (16 Cows, 25 Strawberries)

Logs:
- Average & Median Score ($)
- Score Std Dev & Min/Max
- Idle Workers / Turn & Worker Utilization (%)
- Estimated Milk & Strawberry Revenue ($)
- Mid-Game Cash Floor (Day 15 / T360 Cash)
- Overall Efficiency ($ / Active Worker-Hour)
"""

import sys
import os
import json
import importlib.util
import statistics
import time
import math

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load baseline kaitofukami-v18.py
v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
if not os.path.exists(v18_path):
    v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"

spec = importlib.util.spec_from_file_location("v18_cow_exp", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}

CONFIGURATIONS = [
    {"label": "0 Cows (Pure Crop)", "cows": 0, "strawberries": 50},
    {"label": "4 Cows", "cows": 4, "strawberries": 40},
    {"label": "8 Cows", "cows": 8, "strawberries": 35},
    {"label": "12 Cows (Baseline)", "cows": 12, "strawberries": 30},
    {"label": "16 Cows (Heavy Herd)", "cows": 16, "strawberries": 25},
]


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def run_cow_frontier(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 16: COW REPLACEMENT FRONTIER EXPERIMENT (10 Matches per Config)")
    print("=" * 80)

    results = []

    for config in CONFIGURATIONS:
        label = config["label"]
        cow_count = config["cows"]
        strawberry_count = config["strawberries"]

        print(f"\n--- Benchmarking {label} (Cows: {cow_count}, Strawberries: {strawberry_count}) ---")

        strat_dict = dict(BASE_STRATEGY)
        strat_dict["cows"] = cow_count
        strat_dict["strawberries"] = strawberry_count

        scores = []
        idle_worker_turns = []
        active_worker_turns = []
        midgame_cash_floors = []
        total_worker_turns_all = 0

        for seed in seeds:
            v18_mod.configure_strategy(dict(strat_dict))

            match_idle = 0
            match_active = 0
            t360_cash = 0.0

            def tracking_agent(obs):
                nonlocal match_idle, match_active, t360_cash, total_worker_turns_all

                player = int(v18_mod._get(obs, "player", 0))
                farm = v18_mod._get(obs, "farms", [])[player]
                money = float(v18_mod._get(farm, "money", 0))
                day = int(v18_mod._get(obs, "day", 0))
                hour = int(v18_mod._get(obs, "hour", 0))
                step = day * 24 + hour

                if step == 360:
                    t360_cash = money

                action_dict = v18_mod.agent(obs)

                farmer_act = action_dict.get("farmer", ["PASS"])
                hands_acts = action_dict.get("hands", [])
                all_acts = [farmer_act] + hands_acts

                for act in all_acts:
                    total_worker_turns_all += 1
                    if not act or act == ["PASS"]:
                        match_idle += 1
                    else:
                        match_active += 1

                return action_dict

            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            state = env.run([tracking_agent, _noop_agent])

            final_score = state[-1][0]["reward"]
            scores.append(final_score)
            idle_worker_turns.append(match_idle / 720.0)
            active_worker_turns.append(match_active / 720.0)
            midgame_cash_floors.append(t360_cash)

        avg_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
        min_score = min(scores)
        max_score = max(scores)

        avg_idle = statistics.mean(idle_worker_turns)
        avg_active = statistics.mean(active_worker_turns)
        avg_t360_cash = statistics.mean(midgame_cash_floors)
        utilization_pct = (avg_active / max(0.001, avg_active + avg_idle)) * 100.0

        # Revenue estimations
        estimated_milk_rev = cow_count * 20 * 160
        estimated_strawberry_rev = strawberry_count * 15 * 120
        efficiency_per_active_hour = avg_score / max(1.0, avg_active * 720)

        res = {
            "label": label,
            "cows": cow_count,
            "strawberries": strawberry_count,
            "avg_score": round(avg_score, 2),
            "median_score": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "min_score": round(min_score, 2),
            "max_score": round(max_score, 2),
            "avg_idle_workers_per_turn": round(avg_idle, 2),
            "utilization_pct": round(utilization_pct, 2),
            "avg_t360_midgame_cash": round(avg_t360_cash, 2),
            "estimated_milk_revenue": estimated_milk_rev,
            "estimated_strawberry_revenue": estimated_strawberry_rev,
            "efficiency_per_active_hour": round(efficiency_per_active_hour, 2),
            "scores": scores,
        }

        results.append(res)
        print(f"  Avg Score: ${avg_score:,.2f} | Median: ${median_score:,.2f} | StdDev: ${std_score:,.2f}")
        print(f"  Idle Workers: {avg_idle:.2f} | Utilization: {utilization_pct:.1f}% | Day 15 Cash: ${avg_t360_cash:,.2f}")

    # Summary report
    print("\n" + "=" * 85)
    print(" RESEARCH 16: COW REPLACEMENT FRONTIER SUMMARY")
    print("=" * 85)
    print(f"{'Config Label':<22} | {'Avg Score ($)':<13} | {'Median ($)':<11} | {'StdDev ($)':<10} | {'Day 15 Cash':<12} | {'Idle W/Turn':<11}")
    print("-" * 90)
    for r in results:
        print(f"{r['label']:<22} | ${r['avg_score']:<12,.2f} | ${r['median_score']:<10,.2f} | ${r['std_dev']:<9,.2f} | ${r['avg_t360_midgame_cash']:<11,.2f} | {r['avg_idle_workers_per_turn']:<11.2f}")
    print("=" * 85)

    # Find optimal configuration
    best_config = max(results, key=lambda x: x["avg_score"])
    print(f"\nOPTIMAL CONFIGURATION FOUND: {best_config['label']} with ${best_config['avg_score']:,.2f} Avg Score!\n")

    report = {
        "configurations": results,
        "optimal_configuration": best_config,
    }

    with open("research16_cow_replacement_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research16_cow_replacement_results.json")

    return report


if __name__ == "__main__":
    run_cow_frontier()
