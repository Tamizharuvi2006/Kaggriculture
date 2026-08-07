"""Research 19.5: Fast Parallelized 100-Match Robustness Check (Cows=12 vs Cows=13).

Uses ProcessPoolExecutor across 8 CPU cores to run 200 matches (100 for Cows=12, 100 for Cows=13) in ~30 seconds.
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

V81_BASE_STRATEGY = {
    "use_fixed_schedule": False,
    "opening_melons": 15,
    "strawberries": 30,
    "cows": 12,
    "sheep": 0,
    "land_ne_day": 5,
    "land_sw_day": 7,
}


def _load_v18_module(mod_id=0):
    v18_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "kaitofukami-v18.py")
    if not os.path.exists(v18_path):
        v18_path = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
    spec = importlib.util.spec_from_file_location(f"v18_inst_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_single_match_worker(args):
    cows_count, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V81_BASE_STRATEGY)
        overrides["cows"] = cows_count
        mod.configure_strategy(overrides)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"cows": cows_count, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"cows": cows_count, "seed": seed, "score": 0.0, "error": str(e)}


def main():
    print("=" * 85)
    print(" RESEARCH 19.5: FAST PARALLEL 100-MATCH ROBUSTNESS CHECK (200 Matches)")
    print("=" * 85)

    seeds = list(range(1000, 1100))
    max_workers = 8

    results_by_config = {12: [], 13: []}

    start_time = time.time()

    # Build task list
    tasks = []
    pid = 0
    for cows_count in (12, 13):
        for seed in seeds:
            tasks.append((cows_count, seed, pid))
            pid += 1

    print(f"Launching {len(tasks)} matches across {max_workers} CPU cores...")

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_single_match_worker, task): task for task in tasks}
        for future in as_completed(futures):
            res = future.result()
            cows_count = res["cows"]
            score = res["score"]
            results_by_config[cows_count].append(score)
            completed += 1
            if completed % 40 == 0 or completed == len(tasks):
                print(f"  [Progress {completed}/{len(tasks)} matches completed] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Process results
    c12_scores = results_by_config[12]
    c13_scores = results_by_config[13]

    c12_mean = statistics.mean(c12_scores)
    c12_median = statistics.median(c12_scores)
    c12_std = statistics.stdev(c12_scores)
    c12_worst = min(c12_scores)
    c12_best = max(c12_scores)
    c12_bankrupt = sum(1 for s in c12_scores if s < 10000)

    c13_mean = statistics.mean(c13_scores)
    c13_median = statistics.median(c13_scores)
    c13_std = statistics.stdev(c13_scores)
    c13_worst = min(c13_scores)
    c13_best = max(c13_scores)
    c13_bankrupt = sum(1 for s in c13_scores if s < 10000)

    diff = c13_mean - c12_mean

    report = {
        "cows_12_baseline": {
            "mean": round(c12_mean, 2),
            "median": round(c12_median, 2),
            "std_dev": round(c12_std, 2),
            "worst": round(c12_worst, 2),
            "best": round(c12_best, 2),
            "bankruptcies": c12_bankrupt,
            "scores": c12_scores,
        },
        "cows_13_variant": {
            "mean": round(c13_mean, 2),
            "median": round(c13_median, 2),
            "std_dev": round(c13_std, 2),
            "worst": round(c13_worst, 2),
            "best": round(c13_best, 2),
            "bankruptcies": c13_bankrupt,
            "scores": c13_scores,
        },
        "net_difference_c13_vs_c12": round(diff, 2),
        "total_elapsed_seconds": round(elapsed, 1),
    }

    print("\n" + "=" * 90)
    print(" OFFICIAL 100-MATCH BENCHMARK RESULTS (Seeds 1000-1099)")
    print("=" * 90)
    print(f"{'Configuration':<25} | {'Avg Score ($)':<13} | {'Median ($)':<11} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 95)
    print(f"{'Baseline V8.1 (Cows=12)':<25} | ${c12_mean:<12,.2f} | ${c12_median:<10,.2f} | ${c12_worst:<9,.2f} | ${c12_std:<8,.2f} | {c12_bankrupt:<12}")
    print(f"{'Variant A (Cows=13)':<25} | ${c13_mean:<12,.2f} | ${c13_median:<10,.2f} | ${c13_worst:<9,.2f} | ${c13_std:<8,.2f} | {c13_bankrupt:<12}")
    print("=" * 90)

    if diff > 500 and c13_bankrupt == 0:
        verdict = f"CONFIRMED VICTORY! Cows=13 beats Cows=12 over 100 official matches by +${diff:,.2f} ($121.97k -> ${c13_mean:,.2f}) with 0 bankruptcies!"
    elif diff <= 500 and diff >= -500:
        verdict = f"EQUIVALENT: Cows=13 and Cows=12 perform identically over 100 matches (+${diff:,.2f} diff). Retain Cows=12 baseline."
    else:
        verdict = f"REJECTED: Cows=12 is superior over 100 matches (-${abs(diff):,.2f} drop for Cows=13). Retain Cows=12 baseline."

    print(f"\nFINAL VERDICT: {verdict}\n")
    report["final_verdict"] = verdict

    with open("research19_5_robustness_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full parallel report to research19_5_robustness_results.json")


if __name__ == "__main__":
    main()
