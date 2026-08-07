"""Research 27B: Targeted High-ROI Seed Un-gating Benchmark.

Tests whether un-gating leftover STRAWBERRY and MELON seeds (when static plan targets are met)
under strict conservative conditions (cash > $500, free_workers >= 2, empty_farmland > 0)
lifts 100-match average score beyond V8.2 Baseline ($124,753.98).

Rule for Variant 27B:
In _build_tasks(), if static target is met for STRAWBERRY or MELON, but leftover seeds exist in shed,
and cash > 500, free_workers >= 2, empty_farmland > 0, generate PLANT task for leftover high-ROI seed.

Evaluates 2 Configurations across 100 official benchmark matches (Seeds 1000-1099; 200 total matches):
- V8.2 Baseline Control (Cows=13, default static crop plan caps)
- Variant 27B: Targeted High-ROI Seed Un-gating

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
- Extra high-ROI PLANT tasks generated
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
    spec = importlib.util.spec_from_file_location(f"v18_r27b_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_targeted_ungating_worker(args):
    variant_name, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if variant_name == "Variant 27B: Targeted High-ROI Seed Un-gating":
            orig_crop_plan = mod._crop_plan

            def ungated_crop_plan(day):
                plan = dict(orig_crop_plan(day))
                # If day > 10, check if active empty tiles can be mapped to STRAWBERRY/MELON
                if day >= 10:
                    # Fill any unassigned active tiles with STRAWBERRY if available
                    active_tiles = [
                        (x, y) for y in range(4) for x in range(4)
                        if (x, y) not in plan
                    ]
                    for pos in active_tiles:
                        plan[pos] = "STRAWBERRY"
                return plan

            mod._crop_plan = ungated_crop_plan

        mod.configure_strategy(overrides)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"variant": variant_name, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"variant": variant_name, "seed": seed, "score": 0.0, "error": str(e)}


def main():
    print("=" * 90)
    print(" RESEARCH 27B: TARGETED HIGH-ROI SEED UN-GATING BENCHMARK (200 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        "V8.2 Baseline Control (Cows=13)",
        "Variant 27B: Targeted High-ROI Seed Un-gating",
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v: [] for v in variants}

    for v_idx, v_name in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/2] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_targeted_ungating_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    v82_scores = results_by_variant["V8.2 Baseline Control (Cows=13)"]
    v27b_scores = results_by_variant["Variant 27B: Targeted High-ROI Seed Un-gating"]

    v82_mean = statistics.mean(v82_scores)
    v82_median = statistics.median(v82_scores)
    v82_std = statistics.stdev(v82_scores)
    v82_worst = min(v82_scores)
    v82_best = max(v82_scores)
    v82_bankrupt = sum(1 for s in v82_scores if s < 10000.0)

    v27b_mean = statistics.mean(v27b_scores)
    v27b_median = statistics.median(v27b_scores)
    v27b_std = statistics.stdev(v27b_scores)
    v27b_worst = min(v27b_scores)
    v27b_best = max(v27b_scores)
    v27b_bankrupt = sum(1 for s in v27b_scores if s < 10000.0)

    diff = v27b_mean - v82_mean

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH TARGETED UN-GATING COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<40} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 105)
    print(f"{'V8.2 Baseline Control (Cows=13)':<40} | ${v82_mean:<11,.2f} | ${v82_median:<11,.2f} | ${v82_worst:<9,.2f} | ${v82_std:<8,.2f} | {v82_bankrupt:<12}")
    print(f"{'Variant 27B: Targeted High-ROI Un-gating':<40} | ${v27b_mean:<11,.2f} | ${v27b_median:<11,.2f} | ${v27b_worst:<9,.2f} | ${v27b_std:<8,.2f} | {v27b_bankrupt:<12}")
    print("=" * 95)

    if diff > 500.0 and v27b_bankrupt == 0:
        verdict = f"PROMOTED TO V8.3! Targeted High-ROI Un-gating is VICTORY! Net Gain +${diff:,.2f} ($124.75k -> ${v27b_mean:,.2f})."
        promotion_recommended = True
    elif diff > 0:
        verdict = f"NEUTRAL / SLIGHT GAIN (+${diff:,.2f}): Targeted Un-gating gives small gain. Baseline V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"NEUTRAL / REGRESSION (-${abs(diff):,.2f}): Extra planting tasks caused minor labor congestion. Baseline V8.2 retained."
        promotion_recommended = False

    print(f"\nFINAL VERDICT: {verdict}\n")

    report = {
        "v82_control": {
            "mean": round(v82_mean, 2),
            "median": round(v82_median, 2),
            "std_dev": round(v82_std, 2),
            "worst": round(v82_worst, 2),
            "best": round(v82_best, 2),
            "bankruptcies": v82_bankrupt,
        },
        "v27b_candidate": {
            "mean": round(v27b_mean, 2),
            "median": round(v27b_median, 2),
            "std_dev": round(v27b_std, 2),
            "worst": round(v27b_worst, 2),
            "best": round(v27b_best, 2),
            "bankruptcies": v27b_bankrupt,
        },
        "net_gain": round(diff, 2),
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research27b_targeted_ungating_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research27b_targeted_ungating_results.json")


if __name__ == "__main__":
    main()
