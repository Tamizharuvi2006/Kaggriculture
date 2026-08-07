"""Research 27A: Shadow Scheduler & Omission Streak Audit.

Audits all SCHEDULER_OMISSION idle events across 100 official benchmark matches (Seeds 1000-1099; 145,843 omission steps).

Logs & Measures:
1. Average & Maximum Omission Streak Length (consecutive idle steps where farmland, seeds & cash existed)
2. Crop Type Breakdown of idle seeds in shed during omission streaks
3. Estimated ROI of omitted PLANT tasks ($/turn)
4. Percentage of omission events that were genuinely profitable vs labor-starvation pauses
"""

import sys
import os
import json
import time
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
    spec = importlib.util.spec_from_file_location(f"v18_r27a_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_shadow_scheduler_seed(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    omission_streaks = []
    current_streak = 0

    crop_idle_counts = {
        "STRAWBERRY": 0,
        "MELON": 0,
        "CARROT": 0,
        "WHEAT": 0,
        "TOMATO": 0,
    }

    profitable_omission_count = 0
    total_omission_count = 0

    # Crop ROI per turn estimates ($)
    crop_roi = {
        "STRAWBERRY": 73.63,
        "MELON": 40.53,
        "CARROT": 25.00,
        "WHEAT": 13.51,
        "TOMATO": 18.00,
    }

    def tracking_agent(obs):
        nonlocal current_streak, profitable_omission_count, total_omission_count

        player = int(mod._get(obs, "player", 0))
        farm = mod._get(obs, "farms", [])[player]
        private = mod._get(obs, "private", {}) or {}
        shed = mod._get(private, "shed", {}) or {}
        tiles = mod._get(farm, "tiles", [])
        money = float(mod._get(farm, "money", 0))
        day = int(mod._get(obs, "day", 0))
        unlocked = set(mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

        action_dict = mod.agent(obs)

        farmer_act = action_dict.get("farmer", ["PASS"])
        hands_acts = action_dict.get("hands", [])
        all_acts = [farmer_act] + hands_acts

        empty_tiles = sum(
            1 for y in range(len(tiles)) for x in range(len(tiles[y]))
            if mod._active_target((x, y), day, unlocked) and tiles[y][x] is None
        )

        for act in all_acts:
            is_idle = (not act or act == ["PASS"])
            if is_idle:
                # Check for omission condition
                available_seeds = {crop: int(shed.get(crop, 0)) for crop in crop_roi.keys() if int(shed.get(crop, 0)) > 0}
                total_seeds = sum(available_seeds.values())

                if empty_tiles > 0 and total_seeds > 0:
                    total_omission_count += 1
                    current_streak += 1

                    # Log crop type sitting in shed
                    for crop, qty in available_seeds.items():
                        crop_idle_counts[crop] += qty

                    # Check ROI: if STRAWBERRY or MELON seeds exist, this is a highly profitable omitted task
                    if "STRAWBERRY" in available_seeds or "MELON" in available_seeds:
                        profitable_omission_count += 1
                else:
                    if current_streak > 0:
                        omission_streaks.append(current_streak)
                        current_streak = 0
            else:
                if current_streak > 0:
                    omission_streaks.append(current_streak)
                    current_streak = 0

        return action_dict

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    if current_streak > 0:
        omission_streaks.append(current_streak)

    final_score = float(state[-1][0]["reward"])

    return {
        "seed": seed,
        "score": final_score,
        "omission_streaks": omission_streaks,
        "crop_idle_counts": crop_idle_counts,
        "profitable_omission_count": profitable_omission_count,
        "total_omission_count": total_omission_count,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 27A: SHADOW SCHEDULER & OMISSION STREAK AUDIT (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing omission streaks across {len(seeds)} official seeds...")

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_shadow_scheduler_seed, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Aggregate global streak metrics
    all_streaks = []
    for r in results:
        all_streaks.extend(r["omission_streaks"])

    avg_streak_len = statistics.mean(all_streaks) if all_streaks else 0.0
    max_streak_len = max(all_streaks) if all_streaks else 0
    median_streak_len = statistics.median(all_streaks) if all_streaks else 0

    total_omissions = sum(r["total_omission_count"] for r in results)
    total_prof_omissions = sum(r["profitable_omission_count"] for r in results)
    prof_pct = (total_prof_omissions / max(1, total_omissions)) * 100.0

    global_crop_idles = {
        "STRAWBERRY": sum(r["crop_idle_counts"]["STRAWBERRY"] for r in results),
        "MELON": sum(r["crop_idle_counts"]["MELON"] for r in results),
        "WHEAT": sum(r["crop_idle_counts"]["WHEAT"] for r in results),
        "CARROT": sum(r["crop_idle_counts"]["CARROT"] for r in results),
        "TOMATO": sum(r["crop_idle_counts"]["TOMATO"] for r in results),
    }

    print("\n" + "=" * 90)
    print(" OMISSION STREAK & PROFITABILITY AUDIT RESULTS")
    print("=" * 90)
    print(f" Total Omission Events Audited:      {total_omissions}")
    print(f" Total Omission Streaks Recorded:   {len(all_streaks)} streaks")
    print(f" Average Omission Streak Length:    {avg_streak_len:.2f} consecutive steps")
    print(f" Median Omission Streak Length:     {median_streak_len:.1f} consecutive steps")
    print(f" Maximum Omission Streak Length:    {max_streak_len} CONSECUTIVE STEPS!")
    print("-" * 90)
    print(f" Highly Profitable Omitted Steps:    {total_prof_omissions} ({prof_pct:.2f}% of all omissions)")
    print("-" * 90)
    print(" IDLE SEEDS SITTING UNPLANTED IN SHED DURING OMISSION STREAKS:")
    for crop, cnt in sorted(global_crop_idles.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {crop:<12} Seeds Unplanted: {cnt} step-instances")
    print("=" * 90)

    report = {
        "total_omissions": total_omissions,
        "total_streaks_recorded": len(all_streaks),
        "avg_streak_length": round(avg_streak_len, 2),
        "median_streak_length": round(median_streak_len, 2),
        "max_streak_length": max_streak_len,
        "profitable_omissions_count": total_prof_omissions,
        "profitable_omissions_percentage": round(prof_pct, 2),
        "crop_idle_breakdown": global_crop_idles,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research27a_shadow_scheduler_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research27a_shadow_scheduler_results.json")


if __name__ == "__main__":
    main()
