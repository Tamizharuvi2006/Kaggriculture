"""Step-by-Step Comparative Diagnostic: V4.1 Base Engine vs V8.3 Static Agent.

Analyzes 10 matches turn-by-turn (Step 0 to Step 720) to isolate the exact step
and domain (Feed, Cow Fleet, Land Quadrants, Milk Revenue, Crop Sales)
where the $80,000+ score gap between V4.1 (1714.4 Rating) and V8.3 (816.8 Rating) explodes!
"""

import sys
import os
import json
import time
import importlib.util
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
V83_PATH = r"D:\kaggriculture\baseline\submission_v83_standalone.py"


def _load_v41_engine(mod_id=0):
    spec = importlib.util.spec_from_file_location(f"v41_diag_{mod_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
    })
    return mod


def _load_v83_engine(mod_id=0):
    spec = importlib.util.spec_from_file_location(f"v83_diag_{mod_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "opening_melons": 15,
        "strawberries": 30,
        "cows": 13,
        "sheep": 0,
        "land_ne_day": 5,
        "land_sw_day": 7,
    })
    return mod


def audit_match(seed):
    v41_mod = _load_v41_engine(seed)
    v83_mod = _load_v83_engine(seed + 10000)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([v41_mod.agent, v83_mod.agent])

    step_telemetry = []
    for step_idx in range(len(state_history)):
        if (step_idx + 1) % 24 == 0 or step_idx == len(state_history) - 1:
            farm_v41 = state_history[step_idx][0]["observation"]["farms"][0]
            farm_v83 = state_history[step_idx][1]["observation"]["farms"][1]

            money_v41 = float(farm_v41["money"])
            money_v83 = float(farm_v83["money"])

            cows_v41 = sum(1 for row in farm_v41["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
            cows_v83 = sum(1 for row in farm_v83["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")

            step_telemetry.append({
                "day": (step_idx + 1) // 24,
                "step": step_idx + 1,
                "money_v41": money_v41,
                "money_v83": money_v83,
                "money_gap": money_v41 - money_v83,
                "cows_v41": cows_v41,
                "cows_v83": cows_v83,
            })

    final_v41 = float(state_history[-1][0]["observation"]["farms"][0]["money"])
    final_v83 = float(state_history[-1][1]["observation"]["farms"][1]["money"])

    return {
        "seed": seed,
        "final_v41": final_v41,
        "final_v83": final_v83,
        "gap": final_v41 - final_v83,
        "telemetry": step_telemetry,
    }


def main():
    print("=" * 90)
    print(" COMPARATIVE DIAGNOSTIC: V4.1 BASE ENGINE vs V8.3 STATIC AGENT (10 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1010))
    match_reports = []

    for seed in seeds:
        print(f" Auditing Match Seed {seed}...")
        report = audit_match(seed)
        match_reports.append(report)
        print(f"   -> Seed {seed} Final Money: V4.1 = ${report['final_v41']:,.2f} | V8.3 = ${report['final_v83']:,.2f} | Gap = +${report['gap']:,.2f}")

    # Aggregate telemetry across days
    daily_gaps = defaultdict(list)
    daily_cows_v41 = defaultdict(list)
    daily_cows_v83 = defaultdict(list)

    for r in match_reports:
        for t in r["telemetry"]:
            d = t["day"]
            daily_gaps[d].append(t["money_gap"])
            daily_cows_v41[d].append(t["cows_v41"])
            daily_cows_v83[d].append(t["cows_v83"])

    print("\n" + "=" * 90)
    print(" DAY-BY-DAY MONEY GAP & COW FLEET EVOLUTION (Averaged Across 10 Matches)")
    print("=" * 90)
    print(f"{'Day':<6} | {'V4.1 Money ($)':<16} | {'V8.3 Money ($)':<16} | {'Money Gap ($)':<16} | {'V4.1 Cows':<10} | {'V8.3 Cows':<10}")
    print("-" * 90)

    for day in range(1, 31):
        gaps = daily_gaps[day]
        avg_gap = sum(gaps) / len(gaps)
        avg_c41 = sum(daily_cows_v41[day]) / len(daily_cows_v41[day])
        avg_c83 = sum(daily_cows_v83[day]) / len(daily_cows_v83[day])
        
        # Calculate avg money
        avg_m41 = sum(r["telemetry"][day-1]["money_v41"] for r in match_reports) / len(match_reports)
        avg_m83 = sum(r["telemetry"][day-1]["money_v83"] for r in match_reports) / len(match_reports)

        print(f"Day {day:<2} | ${avg_m41:<15,.2f} | ${avg_m83:<15,.2f} | +${avg_gap:<15,.2f} | {avg_c41:<10.1f} | {avg_c83:<10.1f}")

    print("=" * 90)

    # Save report
    out_data = {
        "match_reports": match_reports,
        "daily_avg_gap": {day: round(sum(daily_gaps[day])/len(daily_gaps[day]), 2) for day in range(1, 31)},
    }
    with open("v41_vs_v83_step_gap_results.json", "w") as f:
        json.dump(out_data, f, indent=2)
    print("\nSaved step-gap diagnostic report to v41_vs_v83_step_gap_results.json")


if __name__ == "__main__":
    main()
