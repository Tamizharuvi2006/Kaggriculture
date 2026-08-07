"""Research 21: Joint Priority Feed & Cow #13 Optimization.

Tests whether combining Priority Feed Purchasing with Cows=13 is additive, redundant, or causes interference.

Evaluates 2 Configurations across 100 official benchmark matches (Seeds 1000-1099; 200 total matches):
- V8.2 Baseline Control: cows = 13, normal feed priority
- Variant A (V8.3 Candidate): cows = 13, priority feed purchasing (BUY_PRODUCT WHEAT moved to top of market orders)

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Peak Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
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
    spec = importlib.util.spec_from_file_location(f"v18_r21_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_joint_worker(args):
    variant_name, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if variant_name == "Variant A: Cows=13 + Priority Feed":
            orig_market_orders = mod._market_orders

            def priority_market_orders(obs):
                orders = orig_market_orders(obs)
                feed_orders = [o for o in orders if len(o) > 1 and o[1] == "WHEAT" and o[0] == "BUY_PRODUCT"]
                other_orders = [o for o in orders if not (len(o) > 1 and o[1] == "WHEAT" and o[0] == "BUY_PRODUCT")]
                return feed_orders + other_orders

            mod._market_orders = priority_market_orders

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
    print(" RESEARCH 21: JOINT PRIORITY FEED & COW #13 BENCHMARK (200 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        "V8.2 Baseline Control (Cows=13)",
        "Variant A: Cows=13 + Priority Feed",
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v: [] for v in variants}

    for v_idx, v_name in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/2] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_joint_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    v82_scores = results_by_variant["V8.2 Baseline Control (Cows=13)"]
    v83_scores = results_by_variant["Variant A: Cows=13 + Priority Feed"]

    v82_mean = statistics.mean(v82_scores)
    v82_median = statistics.median(v82_scores)
    v82_std = statistics.stdev(v82_scores)
    v82_worst = min(v82_scores)
    v82_best = max(v82_scores)
    v82_bankrupt = sum(1 for s in v82_scores if s < 10000.0)

    v83_mean = statistics.mean(v83_scores)
    v83_median = statistics.median(v83_scores)
    v83_std = statistics.stdev(v83_scores)
    v83_worst = min(v83_scores)
    v83_best = max(v83_scores)
    v83_bankrupt = sum(1 for s in v83_scores if s < 10000.0)

    diff = v83_mean - v82_mean

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH JOINT OPTIMIZATION COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<35} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 105)
    print(f"{'V8.2 Baseline Control (Cows=13)':<35} | ${v82_mean:<11,.2f} | ${v82_median:<11,.2f} | ${v82_worst:<9,.2f} | ${v82_std:<8,.2f} | {v82_bankrupt:<12}")
    print(f"{'Variant A: Cows=13 + Priority Feed':<35} | ${v83_mean:<11,.2f} | ${v83_median:<11,.2f} | ${v83_worst:<9,.2f} | ${v83_std:<8,.2f} | {v83_bankrupt:<12}")
    print("=" * 95)

    if diff > 500.0 and v83_bankrupt == 0:
        verdict = f"PROMOTED TO V8.3! Priority Feed + Cows=13 is ADDITIVE! Gain +${diff:,.2f} over V8.2 ($124.75k -> ${v83_mean:,.2f})."
        promotion_recommended = True
    elif diff > 0:
        verdict = f"REDUNDANT: Priority Feed gives small gain (+${diff:,.2f}) over V8.2. Baseline V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"INTERFERENCE / REGRESSION: Priority Feed with Cows=13 decreased score by -${abs(diff):,.2f}. Baseline V8.2 retained."
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
        "v83_candidate": {
            "mean": round(v83_mean, 2),
            "median": round(v83_median, 2),
            "std_dev": round(v83_std, 2),
            "worst": round(v83_worst, 2),
            "best": round(v83_best, 2),
            "bankruptcies": v83_bankrupt,
        },
        "net_gain": round(diff, 2),
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research21_joint_optimization_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research21_joint_optimization_results.json")


if __name__ == "__main__":
    main()
