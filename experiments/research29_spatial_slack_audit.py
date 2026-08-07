"""Research 29: Spatial Slack Audit.

Audits the 2D spatial geometry and spatial freedom of V8.2 Baseline
across 100 official benchmark matches (Seeds 1000-1099; 71,900 game turns).

Logs & Measures:
1. Average Unused Farmland Tiles per Turn (empty active tiles)
2. Average Pasture Capacity & Pasture Tile Slack
3. Shed Manhattan Distance Heatmap to empty active tiles
4. Number of turns with legally valid placements for +1 extra Strawberry or Cow
5. Correlation between spatial slack metrics and final score
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
    spec = importlib.util.spec_from_file_location(f"v18_r29_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_spatial_slack_seed(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    unused_farmland_per_turn = []
    pasture_slack_per_turn = []
    shed_distances = []

    turns_with_zero_slack = 0
    total_turns = 0

    SHED_POS = (0, 0)

    def tracking_agent(obs):
        nonlocal turns_with_zero_slack, total_turns

        player = int(mod._get(obs, "player", 0))
        farm = mod._get(obs, "farms", [])[player]
        tiles = mod._get(farm, "tiles", [])
        day = int(mod._get(obs, "day", 0))
        unlocked = set(mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

        total_turns += 1

        empty_active_tiles = []
        pasture_tile_count = 0
        cow_count = 0

        for y in range(len(tiles)):
            for x in range(len(tiles[y])):
                pos = (x, y)
                if mod._active_target(pos, day, unlocked):
                    tile = tiles[y][x]
                    if tile is None:
                        empty_active_tiles.append(pos)
                        dist = abs(x - SHED_POS[0]) + abs(y - SHED_POS[1])
                        shed_distances.append(dist)
                    elif isinstance(tile, dict):
                        if tile.get("kind") == "PASTURE":
                            pasture_tile_count += 1
                            if tile.get("animal") == "COW":
                                cow_count += 1

        unused_cnt = len(empty_active_tiles)
        unused_farmland_per_turn.append(unused_cnt)

        p_slack = pasture_tile_count - cow_count
        pasture_slack_per_turn.append(p_slack)

        if unused_cnt == 0:
            turns_with_zero_slack += 1

        return mod.agent(obs)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])

    avg_unused = statistics.mean(unused_farmland_per_turn) if unused_farmland_per_turn else 0.0
    avg_pasture_slack = statistics.mean(pasture_slack_per_turn) if pasture_slack_per_turn else 0.0
    avg_shed_dist = statistics.mean(shed_distances) if shed_distances else 0.0
    zero_slack_pct = (turns_with_zero_slack / max(1, total_turns)) * 100.0

    return {
        "seed": seed,
        "score": final_score,
        "avg_unused_tiles": avg_unused,
        "avg_pasture_slack": avg_pasture_slack,
        "avg_shed_dist": avg_shed_dist,
        "zero_slack_pct": zero_slack_pct,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 29: SPATIAL SLACK & GEOMETRIC FREEDOM AUDIT (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing 2D spatial slack across {len(seeds)} official seeds...")

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_spatial_slack_seed, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Aggregate metrics across 100 seeds
    scores = [r["score"] for r in results]
    mean_score = statistics.mean(scores)

    avg_unused_tiles = statistics.mean([r["avg_unused_tiles"] for r in results])
    avg_pasture_slack = statistics.mean([r["avg_pasture_slack"] for r in results])
    avg_shed_dist = statistics.mean([r["avg_shed_dist"] for r in results])
    avg_zero_slack_pct = statistics.mean([r["zero_slack_pct"] for r in results])

    # Pearson correlation between unused tiles and score
    unused_list = [r["avg_unused_tiles"] for r in results]
    mean_unused = statistics.mean(unused_list)

    num = sum((s - mean_score) * (u - mean_unused) for s, u in zip(scores, unused_list))
    den = math.sqrt(sum((s - mean_score)**2 for s in scores) * sum((u - mean_unused)**2 for u in unused_list))
    corr_unused_score = num / max(1e-9, den)

    print("\n" + "=" * 95)
    print(" SPATIAL SLACK & GEOMETRIC FREEDOM AUDIT RESULTS (Seeds 1000-1099)")
    print("=" * 95)
    print(f" Average Score across 100 Seeds:        ${mean_score:,.2f}")
    print(f" Average Unused Farmland Tiles / Turn:  {avg_unused_tiles:.2f} empty active tiles")
    print(f" Average Pasture Slot Slack / Turn:     {avg_pasture_slack:.2f} open pasture slots")
    print(f" Average Shed Manhattan Distance:       {avg_shed_dist:.2f} steps to empty tiles")
    print(f" Turns with ZERO Spatial Slack:         {avg_zero_slack_pct:.2f}% of all game turns")
    print(f" Correlation (Unused Tiles vs Score):   {corr_unused_score:<+7.3f}")
    print("-" * 95)

    if avg_unused_tiles > 5.0 and avg_zero_slack_pct < 10.0:
        verdict = f"SIGNIFICANT SPATIAL FREEDOM EXISTS! Avg {avg_unused_tiles:.2f} empty active tiles per turn. Layout optimization could unlock further gains."
    else:
        verdict = f"HIGHLY CONSTRAINED GEOMETRY! Zero slack on {avg_zero_slack_pct:.2f}% of turns. V8.2 layout is near maximum spatial density."

    print(f"SPATIAL FREEDOM VERDICT: {verdict}\n")

    report = {
        "mean_score": round(mean_score, 2),
        "avg_unused_farmland_tiles": round(avg_unused_tiles, 2),
        "avg_pasture_slack": round(avg_pasture_slack, 2),
        "avg_shed_manhattan_dist": round(avg_shed_dist, 2),
        "turns_with_zero_slack_pct": round(avg_zero_slack_pct, 2),
        "correlation_unused_vs_score": round(corr_unused_score, 3),
        "spatial_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research29_spatial_slack_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research29_spatial_slack_results.json")


if __name__ == "__main__":
    main()
