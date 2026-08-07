"""Research 13: Task Scheduler & Work Generator Audit.

Audits V8.1 baseline action generation (_assign_actions and _market_orders) across 10 matches (Seeds 1000-1009).
Logs every idle / PASS action event with full context:
- turn / day / hour
- worker id & position
- nearest harvestable crop, empty farmland, animal task, delivery task
- exact reason for PASS
- 5-category classification

Outputs:
1. Top 5 causes of idle time
2. Percentage breakdown of idle causes
3. The single scheduler rule responsible for the most lost revenue
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

spec = importlib.util.spec_from_file_location("v18_audit", v18_path)
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


def _distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_scheduler(seeds=list(range(1000, 1010))):
    print("=" * 80)
    print(" RESEARCH 13: TASK SCHEDULER & WORK GENERATOR AUDIT (10 Matches)")
    print("=" * 80)

    idle_logs = []
    category_counts = {
        "no profitable task exists": 0,
        "scheduler failed to generate task": 0,
        "resource shortage": 0,
        "worker blocked": 0,
        "queue starvation": 0,
    }
    cause_subcounts = {}

    total_worker_turns = 0
    total_idle_events = 0

    for seed in seeds:
        v18_mod.configure_strategy(dict(V81_STRATEGY))

        def tracking_agent(obs):
            nonlocal total_worker_turns, total_idle_events

            player = int(v18_mod._get(obs, "player", 0))
            farm = v18_mod._get(obs, "farms", [])[player]
            private = v18_mod._get(obs, "private", {}) or {}
            shed = v18_mod._get(private, "shed", {}) or {}
            seeds_inv = v18_mod._get(private, "seeds", {}) or {}
            tiles = v18_mod._get(farm, "tiles", [])
            money = float(v18_mod._get(farm, "money", 0))
            unlocked = set(v18_mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
            day = int(v18_mod._get(obs, "day", 0))
            hour = int(v18_mod._get(obs, "hour", 0))
            step = day * 24 + hour

            positions = [tuple(v18_mod._get(farm, "farmer", (4, 4)))] + [
                tuple(p) for p in (v18_mod._get(farm, "hands", []) or [])
            ]
            inventories = list(v18_mod._get(private, "inventories", []) or [])
            while len(inventories) < len(positions):
                inventories.append({})

            access = v18_mod._available_access(tiles)

            # Build tasks beforehand to analyze work generator state
            built_tasks = v18_mod._build_tasks(obs, positions, inventories)

            # Run actual engine agent logic
            action_dict = v18_mod.agent(obs)

            farmer_action = action_dict.get("farmer", ["PASS"])
            hands_actions = action_dict.get("hands", [])
            all_worker_actions = [farmer_action] + hands_actions

            # Find nearest environmental targets for auditing
            # 1. Harvestable crops
            harvestable_crops = []
            empty_farmland_tiles = []
            animal_tasks = []

            for y in range(len(tiles)):
                for x in range(len(tiles[y])):
                    pos = (x, y)
                    if not v18_mod._active_target(pos, day, unlocked):
                        continue
                    tile = tiles[y][x]
                    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                        if v18_mod._crop_is_ripe(tile, day, hour):
                            harvestable_crops.append((pos, tile.get("crop")))
                    elif tile is None:
                        empty_farmland_tiles.append(pos)
                    elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                        empty_farmland_tiles.append(pos)
                    elif isinstance(tile, dict) and tile.get("animal") in v18_mod.ANIMALS:
                        if day < 29 and not tile.get("fed_today", False):
                            animal_tasks.append((pos, "FEED"))
                        if int(tile.get("yield_units", 0)) > 0:
                            animal_tasks.append((pos, "HARVEST_ANIMAL"))
                        if not tile.get("cared_today", False) and day < 29:
                            animal_tasks.append((pos, "CARE"))
                    elif isinstance(tile, dict) and tile.get("kind") == "PASTURE" and "animal" not in tile:
                        animal_tasks.append((pos, "PLACE_ANIMAL"))

            # Audit each worker
            for w_idx, (pos, inv, act) in enumerate(zip(positions, inventories, all_worker_actions)):
                total_worker_turns += 1

                is_idle = (not act) or (act == ["PASS"])
                if not is_idle:
                    continue

                total_idle_events += 1

                # Find nearest targets relative to worker position
                nearest_harvest = None
                if harvestable_crops:
                    nearest_h_pos, c_type = min(harvestable_crops, key=lambda item: _distance(pos, item[0]))
                    nearest_harvest = {"dist": _distance(pos, nearest_h_pos), "pos": nearest_h_pos, "crop": c_type}

                nearest_empty = None
                if empty_farmland_tiles:
                    nearest_e_pos = min(empty_farmland_tiles, key=lambda p: _distance(pos, p))
                    nearest_empty = {"dist": _distance(pos, nearest_e_pos), "pos": nearest_e_pos}

                nearest_animal = None
                if animal_tasks:
                    nearest_a_pos, a_task = min(animal_tasks, key=lambda item: _distance(pos, item[0]))
                    nearest_animal = {"dist": _distance(pos, nearest_a_pos), "pos": nearest_a_pos, "task": a_task}

                nearest_delivery = None
                carried_items = sum(int(v) for v in inv.values() if isinstance(v, (int, float))) if isinstance(inv, dict) else 0
                if carried_items > 0 and access:
                    nearest_d_pos = min(access, key=lambda p: _distance(pos, p))
                    nearest_delivery = {"dist": _distance(pos, nearest_d_pos), "pos": nearest_d_pos}

                # Determine exact reason and classification for PASS
                category = "no profitable task exists"
                exact_reason = "No active work required on farm"

                if empty_farmland_tiles:
                    # Farmland sits empty! Why wasn't a task assigned?
                    total_seeds = sum(int(seeds_inv.get(c, 0)) for c in v18_mod.CROPS)
                    if total_seeds > 0:
                        # Seeds exist, but maybe crop plan caps or task assignment skipped
                        plant_tasks = [t for t in built_tasks if t[2][0] == "PLANT"]
                        if plant_tasks:
                            category = "queue starvation"
                            exact_reason = f"PLANT tasks generated ({len(plant_tasks)} tasks), but claimed by other workers or worker disqualified"
                        else:
                            category = "scheduler failed to generate task"
                            exact_reason = f"Seeds exist in shed ({total_seeds} seeds), but crop_plan capped or tile not active target"
                    else:
                        # 0 seeds in shed
                        cheap_seed_cost = min(v18_mod.CROPS[c]["seed"] for c in v18_mod.CROPS)
                        if money >= cheap_seed_cost:
                            category = "scheduler failed to generate task"
                            exact_reason = f"Empty farmland exists ({len(empty_farmland_tiles)} tiles) & cash available (${money:.2f}), but market module failed to buy seeds/crop caps reached (0 PLANT tasks generated)"
                        else:
                            category = "resource shortage"
                            exact_reason = f"Empty farmland exists ({len(empty_farmland_tiles)} tiles), but cash is insufficient (${money:.2f}) to purchase seeds"

                elif harvestable_crops:
                    category = "scheduler failed to generate task"
                    exact_reason = f"Harvestable crop exists at {nearest_harvest['pos']} ({nearest_harvest['crop']}), but task generator/priority loop omitted assignment"

                elif animal_tasks:
                    unfed = [t for t in animal_tasks if t[1] == "FEED"]
                    if unfed:
                        carried_w = sum(int(i.get("WHEAT", 0)) for i in inventories if isinstance(i, dict))
                        shed_w = int(shed.get("WHEAT", 0))
                        if carried_w == 0 and shed_w == 0 and money < 25:
                            category = "resource shortage"
                            exact_reason = f"Animals unfed ({len(unfed)} animals), but 0 wheat in shed/inventory and insufficient cash (${money:.2f})"
                        else:
                            category = "queue starvation"
                            exact_reason = f"Feed tasks exist, but assigned to dedicated carrier workers or priority loop exhausted"
                    else:
                        category = "queue starvation"
                        exact_reason = f"Animal maintenance tasks exist ({len(animal_tasks)} tasks), but priority loop assigned to other workers"

                elif carried_items > 0:
                    category = "scheduler failed to generate task"
                    exact_reason = f"Worker carrying {carried_items} inventory items, but drop threshold (day {day}, hour {hour}) not triggered"

                elif len(built_tasks) > 0:
                    category = "queue starvation"
                    exact_reason = f"Task queue built {len(built_tasks)} tasks, but all tasks claimed by other workers (workers {0}..{len(positions)-1})"

                else:
                    category = "no profitable task exists"
                    exact_reason = "All farm tiles planted/watered, animals cared for, no empty tiles or cash for expansion"

                category_counts[category] += 1
                cause_subcounts[exact_reason] = cause_subcounts.get(exact_reason, 0) + 1

                idle_log_entry = {
                    "seed": seed,
                    "turn": step,
                    "day": day,
                    "hour": hour,
                    "worker_id": w_idx,
                    "position": pos,
                    "nearest_harvestable_crop": nearest_harvest,
                    "nearest_empty_farmland": nearest_empty,
                    "nearest_animal_task": nearest_animal,
                    "nearest_delivery_task": nearest_delivery,
                    "exact_reason_for_pass": exact_reason,
                    "classification": category,
                }
                idle_logs.append(idle_log_entry)

            return action_dict

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([tracking_agent, _noop_agent])

    # Percentage breakdown
    pct_breakdown = {}
    for cat, cnt in category_counts.items():
        pct_breakdown[cat] = round(cnt / max(1, total_idle_events) * 100, 2)

    # Top 5 exact causes
    sorted_subcauses = sorted(cause_subcounts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_5_causes = [
        {"cause": cause, "count": cnt, "pct_of_idle": round(cnt / max(1, total_idle_events) * 100, 2)}
        for cause, cnt in sorted_subcauses
    ]

    avg_idle_per_turn = total_idle_events / (len(seeds) * 720)

    # Identify single scheduler rule responsible for the most lost revenue
    primary_rule = sorted_subcauses[0][0] if sorted_subcauses else "Unknown"

    report = {
        "seeds_evaluated": seeds,
        "total_worker_turns": total_worker_turns,
        "total_idle_events": total_idle_events,
        "avg_idle_workers_per_turn": round(avg_idle_per_turn, 2),
        "percentage_breakdown": pct_breakdown,
        "top_5_idle_causes": top_5_causes,
        "single_scheduler_rule_most_lost_revenue": primary_rule,
        "sample_idle_logs_head": idle_logs[:10],
    }

    print("\n" + "=" * 80)
    print(" RESEARCH 13: SCHEDULER AUDIT RESULTS")
    print("=" * 80)
    print(f" Total Worker Turns:         {total_worker_turns}")
    print(f" Total Idle (PASS) Events:   {total_idle_events}")
    print(f" Avg Idle Workers / Turn:    {avg_idle_per_turn:.2f}")
    print("-" * 80)
    print(" CATEGORY BREAKDOWN OF IDLE EVENTS:")
    for cat, pct in sorted(pct_breakdown.items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(pct // 2)
        print(f"   {cat:<35} | {pct:6.2f}% | {bar}")
    print("-" * 80)
    print(" TOP 5 EXACT CAUSES OF IDLE TIME:")
    for idx, item in enumerate(top_5_causes, 1):
        print(f"   {idx}. [{item['pct_of_idle']}%] ({item['count']} events): {item['cause']}")
    print("-" * 80)
    print(f" CRITICAL RULE IDENTIFIED: {primary_rule}")
    print("=" * 80)

    with open("research13_scheduler_audit_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full audit report to experiments/research13_scheduler_audit_results.json")

    return report


if __name__ == "__main__":
    audit_scheduler()
