"""Research 11: Capacity Bottleneck Analysis.

Runs V8.1 baseline across 10 official matches (Seeds 1000-1009) and logs fine-grained
worker task activity from agent action commands, idle counts, free farmland, and time allocation breakdown.
"""

import sys
import os
import json
import importlib.util
import statistics
import time

sys.path.insert(0, r"C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages")
sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

# Load V18 baseline module
v18_path = r"D:\kaggleculture_repo\kaggleculture-main\reference\kaitofukami-v18.py"
spec = importlib.util.spec_from_file_location("v18_bottleneck", v18_path)
v18_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v18_mod)

V81_STRATEGY = {
    "use_fixed_schedule": False,
    "strawberries": 30,
    "opening_melons": 15,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def classify_worker_action(action_list):
    if not action_list or action_list == ["PASS"]:
        return "IDLE / WAITING"
    
    cmd_str = " ".join([str(a) for a in action_list]).upper()

    if "HARVEST" in cmd_str:
        return "HARVESTING"
    elif "PLANT" in cmd_str:
        return "PLANTING"
    elif any(k in cmd_str for k in ("MILK", "FEED", "SHEAR", "BUILD_PASTURE", "PASTURE")):
        return "HERDING & ANIMAL CARE"
    elif "DROP" in cmd_str or "STORE" in cmd_str or "DELIVER" in cmd_str:
        return "DELIVERING TO SHED"
    elif any(k in cmd_str for k in ("NORTH", "SOUTH", "EAST", "WEST", "MOVE", "GOTO")):
        return "WALKING / TRANSIT"
    elif "PICKUP" in cmd_str or "BUY" in cmd_str:
        return "RESOURCE FETCH / PURCHASING"
    else:
        return "OTHER"


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def analyze_capacity_bottleneck(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 11: CAPACITY BOTTLENECK ANALYSIS (10 Matches)")
    print("=" * 80)

    task_counters = {
        "WALKING / TRANSIT": 0,
        "HERDING & ANIMAL CARE": 0,
        "HARVESTING": 0,
        "PLANTING": 0,
        "DELIVERING TO SHED": 0,
        "RESOURCE FETCH / PURCHASING": 0,
        "IDLE / WAITING": 0,
        "OTHER": 0,
    }

    daily_idle_workers = []
    daily_free_farmland = []
    daily_cash = []

    total_worker_steps = 0

    for seed in seeds:
        v18_mod.configure_strategy(dict(V81_STRATEGY))

        def tracking_agent(obs):
            nonlocal total_worker_steps
            action_dict = v18_mod.agent(obs)

            farm = obs["farms"][0]
            tiles = farm.get("tiles", [])
            money = farm.get("money", 0)
            unlocked = farm.get("unlocked_quadrants", ["NW"])

            # Free farmland count
            unlocked_tiles = len(unlocked) * 25
            occupied_tiles = 0
            for y in range(len(tiles)):
                for x in range(len(tiles[y])):
                    if isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") in ("PLANT", "PASTURE"):
                        occupied_tiles += 1

            free_farmland = max(0, unlocked_tiles - occupied_tiles - 14)
            daily_free_farmland.append(free_farmland)
            daily_cash.append(money)

            farmer_action = action_dict.get("farmer", ["PASS"])
            hands_actions = action_dict.get("hands", [])

            all_worker_actions = [farmer_action] + hands_actions
            step_idle_count = 0

            for w_act in all_worker_actions:
                total_worker_steps += 1
                cat = classify_worker_action(w_act)
                task_counters[cat] += 1
                if cat == "IDLE / WAITING":
                    step_idle_count += 1

            daily_idle_workers.append(step_idle_count)
            return action_dict

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([tracking_agent, _noop_agent])

    # Compute percentage breakdown
    percentage_breakdown = {}
    for cat, count in task_counters.items():
        percentage_breakdown[cat] = round(count / max(1, total_worker_steps) * 100, 2)

    avg_idle_workers = statistics.mean(daily_idle_workers)
    avg_free_farmland = statistics.mean(daily_free_farmland)
    avg_cash = statistics.mean(daily_cash)

    sorted_cats = sorted(percentage_breakdown.items(), key=lambda x: x[1], reverse=True)
    top_cat, top_pct = sorted_cats[0]
    sec_cat, sec_pct = sorted_cats[1]

    primary_bottleneck = f"{top_cat} ({top_pct}%) & {sec_cat} ({sec_pct}%)"

    report = {
        "total_worker_steps_evaluated": total_worker_steps,
        "percentage_breakdown": percentage_breakdown,
        "avg_idle_workers_per_step": round(avg_idle_workers, 2),
        "avg_free_unlocked_farmland_tiles": round(avg_free_farmland, 1),
        "avg_cash_balance": round(avg_cash, 1),
        "primary_bottleneck_identified": primary_bottleneck,
    }

    print("\n" + "=" * 80)
    print(" WORKER TIME ALLOCATION BREAKDOWN (% of Total Worker-Hours)")
    print("=" * 80)
    for cat, pct in sorted(percentage_breakdown.items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(pct // 2)
        print(f" {cat:<28} | {pct:6.2f}% | {bar}")
    print("-" * 80)
    print(f" Avg Idle Workers / Step:   {avg_idle_workers:.2f} workers")
    print(f" Avg Free Farmland Tiles:   {avg_free_farmland:.1f} tiles")
    print(f" Avg Cash Balance:          ${avg_cash:,.2f}")
    print(f" PRIMARY BOTTLENECK:        {primary_bottleneck}")
    print("=" * 80)

    with open("research11_capacity_bottleneck_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved report to research11_capacity_bottleneck_results.json")

    return report


if __name__ == "__main__":
    analyze_capacity_bottleneck()
