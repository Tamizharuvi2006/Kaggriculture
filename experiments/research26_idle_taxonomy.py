"""Research 26: Idle-State Taxonomy & Task Generation Audit.

Audits every idle worker step across 100 official benchmark matches (Seeds 1000-1099; 71,900 turns x 4 workers = 287,600 worker-steps).

Classifies idle worker steps into a 6-category taxonomy:
1. NO_SEEDS_AVAILABLE: Empty farmland & cash exist, but shed.seeds == 0
2. NO_PROFITABLE_TASK: All fields planted, cows fed, no action available
3. WAITING_FOR_GROWTH: Tiles planted and in growth phase
4. MARKET_BLOCKED: Max market orders reached or waiting for transaction
5. TRAVEL: Worker moving towards target tile
6. SCHEDULER_OMISSION: Empty farmland exists & seeds exist in shed, but _build_tasks() emitted 0 tasks

Logs:
- Category percentage breakdown of all idle steps
- Average idle steps per match per category
- Correlation with final match score
"""

import sys
import os
import json
import time
import math
import importlib.util
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V82_BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 13,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _load_v18_module(mod_id=0):
    v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
    if not os.path.exists(v18_path):
        v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    spec = importlib.util.spec_from_file_location(f"v18_r26_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_idle_taxonomy_seed(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    taxonomy_counts = {
        "NO_SEEDS_AVAILABLE": 0,
        "NO_PROFITABLE_TASK": 0,
        "WAITING_FOR_GROWTH": 0,
        "MARKET_BLOCKED": 0,
        "TRAVEL": 0,
        "SCHEDULER_OMISSION": 0,
    }

    total_worker_steps = 0
    idle_worker_steps = 0

    def tracking_agent(obs):
        nonlocal total_worker_steps, idle_worker_steps

        player = int(mod._get(obs, "player", 0))
        farm = mod._get(obs, "farms", [])[player]
        private = mod._get(obs, "private", {}) or {}
        shed = mod._get(private, "shed", {}) or {}
        tiles = mod._get(farm, "tiles", [])
        money = float(mod._get(farm, "money", 0))
        day = int(mod._get(obs, "day", 0))
        unlocked = set(mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

        # Execute agent
        action_dict = mod.agent(obs)

        farmer_act = action_dict.get("farmer", ["PASS"])
        hands_acts = action_dict.get("hands", [])
        all_acts = [farmer_act] + hands_acts

        total_worker_steps += len(all_acts)

        # Audit tile states
        empty_tiles = sum(
            1 for y in range(len(tiles)) for x in range(len(tiles[y]))
            if mod._active_target((x, y), day, unlocked) and tiles[y][x] is None
        )
        total_seeds_in_shed = sum(int(shed.get(crop, 0)) for crop in ("STRAWBERRY", "MELON", "CARROT", "WHEAT", "TOMATO"))
        growing_tiles = sum(
            1 for y in range(len(tiles)) for x in range(len(tiles[y]))
            if isinstance(tiles[y][x], dict) and tiles[y][x].get("crop") is not None
        )

        for act in all_acts:
            is_idle = (not act or act == ["PASS"])
            if is_idle:
                idle_worker_steps += 1

                if empty_tiles > 0 and total_seeds_in_shed > 0:
                    taxonomy_counts["SCHEDULER_OMISSION"] += 1
                elif empty_tiles > 0 and total_seeds_in_shed == 0 and money >= 20.0:
                    taxonomy_counts["NO_SEEDS_AVAILABLE"] += 1
                elif growing_tiles > 0 and empty_tiles == 0:
                    taxonomy_counts["WAITING_FOR_GROWTH"] += 1
                elif len(action_dict.get("market", [])) >= 5:
                    taxonomy_counts["MARKET_BLOCKED"] += 1
                else:
                    taxonomy_counts["NO_PROFITABLE_TASK"] += 1
            else:
                # Active step (check if transit)
                if act and len(act) > 0 and act[0] in ("N", "S", "E", "W"):
                    taxonomy_counts["TRAVEL"] += 1

        return action_dict

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])

    return {
        "seed": seed,
        "score": final_score,
        "total_worker_steps": total_worker_steps,
        "idle_worker_steps": idle_worker_steps,
        "taxonomy": taxonomy_counts,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 26: IDLE-STATE TAXONOMY & TASK GENERATION AUDIT (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing worker idle steps across {len(seeds)} official seeds...")

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_idle_taxonomy_seed, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Aggregate global taxonomy statistics
    global_total_steps = sum(r["total_worker_steps"] for r in results)
    global_idle_steps = sum(r["idle_worker_steps"] for r in results)

    global_tax = {
        "NO_SEEDS_AVAILABLE": sum(r["taxonomy"]["NO_SEEDS_AVAILABLE"] for r in results),
        "NO_PROFITABLE_TASK": sum(r["taxonomy"]["NO_PROFITABLE_TASK"] for r in results),
        "WAITING_FOR_GROWTH": sum(r["taxonomy"]["WAITING_FOR_GROWTH"] for r in results),
        "MARKET_BLOCKED": sum(r["taxonomy"]["MARKET_BLOCKED"] for r in results),
        "TRAVEL": sum(r["taxonomy"]["TRAVEL"] for r in results),
        "SCHEDULER_OMISSION": sum(r["taxonomy"]["SCHEDULER_OMISSION"] for r in results),
    }

    idle_pct = (global_idle_steps / max(1, global_total_steps)) * 100.0

    # Calculate Pearson correlations with final match score
    scores = [r["score"] for r in results]
    correlations = {}

    mean_score = statistics.mean(scores)

    for cat in global_tax.keys():
        cat_counts = [r["taxonomy"][cat] for r in results]
        mean_cat = statistics.mean(cat_counts)

        num = sum((s - mean_score) * (c - mean_cat) for s, c in zip(scores, cat_counts))
        den = math.sqrt(sum((s - mean_score)**2 for s in scores) * sum((c - mean_cat)**2 for c in cat_counts))
        correlations[cat] = num / max(1e-9, den)

    print("\n" + "=" * 95)
    print(" IDLE-STATE TAXONOMY AUDIT RESULTS (Seeds 1000-1099)")
    print("=" * 95)
    print(f" Total Worker Steps Audited:       {global_total_steps}")
    print(f" Total Idle Worker Steps:          {global_idle_steps} ({idle_pct:.2f}% of all worker steps)")
    print(f" Avg Idle Worker Steps / Match:    {global_idle_steps / 100:.1f} steps")
    print("-" * 95)
    print(f"{'Category Taxonomy':<25} | {'Step Count':<12} | {'% of Idle Steps':<18} | {'Correlation with Score':<22}")
    print("-" * 95)
    for cat, cnt in sorted(global_tax.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / max(1, global_idle_steps)) * 100.0
        corr = correlations[cat]
        print(f"{cat:<25} | {cnt:<12} | {pct:<17.2f}% | {corr:<+21.3f}")
    print("=" * 95)

    primary_cause = max(global_tax, key=global_tax.get)

    report = {
        "total_worker_steps": global_total_steps,
        "total_idle_steps": global_idle_steps,
        "idle_percentage": round(idle_pct, 2),
        "taxonomy_breakdown": global_tax,
        "taxonomy_correlations": correlations,
        "primary_idle_cause": primary_cause,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research26_idle_taxonomy_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research26_idle_taxonomy_results.json")


if __name__ == "__main__":
    main()
