"""Research 10: SE Integration Feasibility.

Modifies the V18 engine copy dynamically to support Quadrant 4 (SE) land expansion
and crop planning across all 96 tiles.

Phase A: SE Market Order Integration
- Checks land_se_day (e.g. Day 11), "SW" in unlocked, "SE" not in unlocked, budget >= 4000.
- Appends ["BUY_LAND"] for SE.

Phase B: Full Crop Planner Integration
- Updates candidate tile filter in _build_crop_plan to include SE (x>=5, y>=5).

Phase C: 20-Match Official Benchmark (Seeds 1000-1019)
- Compares V8.1 Baseline vs V8.1 + Full SE Support.
- Measures average score, peak, worst, SE land occupancy %, and SE revenue.
"""

import sys
import os
import json
import importlib.util
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"C:\Users\43731140\AppData\Roaming\Python\Python311\site-packages")
sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

_MOD_COUNTER = 0


def _load_v18_se_module(enable_se_market=True, enable_se_crops=True):
    """Loads V18 module with SE market orders and/or SE crop planning enabled."""
    global _MOD_COUNTER
    _MOD_COUNTER += 1
    v18_path = r"D:\kaggleculture_repo\kaggleculture-main\reference\kaitofukami-v18.py"
    
    with open(v18_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Phase B: Patch _build_crop_plan to include SE quadrant tiles (x>=5, y>=5)
    if enable_se_crops:
        old_crop_cond = "if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))"
        new_crop_cond = "if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5) or (x >= 5 and y >= 5))"
        code = code.replace(old_crop_cond, new_crop_cond)

    # 2. Phase A: Patch _market_orders to support BUY_LAND for SE
    if enable_se_market:
        old_land_block = """    elif (
        day >= int(STRATEGY.get("land_sw_day", 10))
        and "NE" in unlocked
        and "SW" not in unlocked
        and budget - operating_reserve >= 2000
    ):
        land_cost = 2000"""

        new_land_block = """    elif (
        day >= int(STRATEGY.get("land_sw_day", 10))
        and "NE" in unlocked
        and "SW" not in unlocked
        and budget - operating_reserve >= 2000
    ):
        land_cost = 2000
    elif (
        day >= int(STRATEGY.get("land_se_day", 11))
        and "SW" in unlocked
        and "SE" not in unlocked
        and budget - operating_reserve >= 4000
    ):
        land_cost = 4000"""
        code = code.replace(old_land_block, new_land_block)

    # Exec patched module
    module_name = f"v18_se_inst_{_MOD_COUNTER}"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(code, mod.__dict__)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_se_match_worker(args):
    strategy_overrides, seed, enable_se_market, enable_se_crops, mod_id = args
    try:
        mod = _load_v18_se_module(enable_se_market, enable_se_crops)
        overrides = dict(strategy_overrides)
        overrides["use_fixed_schedule"] = False
        mod.configure_strategy(overrides)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = last_step[0]["observation"]["farms"][0]["money"]

        # Track SE unlock & tile occupancy
        se_unlocked = False
        se_unlock_day = None
        se_occupied_count = 0

        for step_data in env.steps:
            farm = step_data[0]["observation"]["farms"][0]
            unlocked = farm.get("unlocked_quadrants", [])
            if "SE" in unlocked:
                if not se_unlocked:
                    se_unlocked = True
                    se_unlock_day = step_data[0]["observation"].get("day", 0)
                
                # Count SE occupied tiles
                tiles = farm.get("tiles", [])
                curr_se_occ = 0
                for y in range(5, 10):
                    for x in range(5, 10):
                        if y < len(tiles) and x < len(tiles[y]) and isinstance(tiles[y][x], dict):
                            if tiles[y][x].get("kind") in ("PLANT", "PASTURE"):
                                curr_se_occ += 1
                se_occupied_count = max(se_occupied_count, curr_se_occ)

        return {
            "seed": seed,
            "score": score,
            "se_unlocked": se_unlocked,
            "se_unlock_day": se_unlock_day,
            "se_occupied_count": se_occupied_count,
            "se_occupancy_pct": round(se_occupied_count / 21.0 * 100, 1),
            "error": None
        }
    except Exception as e:
        return {"seed": seed, "score": 0, "se_unlocked": False, "error": str(e)}


def run_research10_feasibility(seeds=list(range(1000, 1020))):
    print("=" * 80)
    print(" RESEARCH 10: SE INTEGRATION FEASIBILITY (20 Official Matches)")
    print("=" * 80)

    strategy_v81 = {
        "strawberries": 30,
        "opening_melons": 15,
        "cows": 12,
        "sheep": 0,
        "land_ne_day": 5,
        "land_sw_day": 7,
        "land_se_day": 11
    }

    variants = [
        ("V8.1 Baseline (75 Tiles, No SE)", False, False),
        ("V8.1 + SE Unlock Only", True, False),
        ("V8.1 + Full SE Support (96 Tiles)", True, True)
    ]

    all_variant_results = {}

    for var_name, se_market, se_crops in variants:
        print(f"\nEvaluating Variant: {var_name}...")
        start_t = time.time()
        tasks = [(strategy_v81, seed, se_market, se_crops, idx) for idx, seed in enumerate(seeds)]
        
        results = []
        with ProcessPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(_run_se_match_worker, t) for t in tasks]
            for f in as_completed(futures):
                results.append(f.result())

        elapsed = time.time() - start_t
        scores = [r["score"] for r in results if r["error"] is None]
        avg_s = statistics.mean(scores)
        med_s = statistics.median(scores)
        max_s = max(scores)
        min_s = min(scores)

        unlocked_matches = sum(1 for r in results if r["se_unlocked"])
        avg_se_occ = statistics.mean([r["se_occupied_count"] for r in results if r["error"] is None])

        all_variant_results[var_name] = {
            "avg": round(avg_s, 1),
            "median": round(med_s, 1),
            "best": round(max_s, 1),
            "worst": round(min_s, 1),
            "se_unlock_rate": f"{unlocked_matches}/{len(seeds)} ({unlocked_matches/len(seeds)*100:.0f}%)",
            "avg_se_tiles_occupied": round(avg_se_occ, 1),
            "se_occupancy_pct": round(avg_se_occ / 21.0 * 100, 1),
            "elapsed_s": round(elapsed, 1)
        }

    print("\n" + "=" * 90)
    print(f"{'Variant':<35} | {'Avg Score':>10} | {'Best':>10} | {'Worst':>10} | {'SE Unlocks':>12} | {'SE Occupancy':>12}")
    print("-" * 90)
    for var_name, res in all_variant_results.items():
        print(f"{var_name:<35} | ${res['avg']:>9,.0f} | ${res['best']:>9,.0f} | ${res['worst']:>9,.0f} | {res['se_unlock_rate']:>12} | {res['se_occupancy_pct']:>11.1f}%")
    print("=" * 90)

    with open("research10_se_feasibility_results.json", "w") as f:
        json.dump(all_variant_results, f, indent=2)
    print("\nSaved results to research10_se_feasibility_results.json")

    return all_variant_results


if __name__ == "__main__":
    run_research10_feasibility()
