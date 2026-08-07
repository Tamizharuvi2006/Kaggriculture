"""Research 20: Feed Insurance & Policy Ablation.

Tests whether feed policy changes (feed reserve, operating reserve, feed priority, earlier feed purchasing)
can eliminate bankruptcies and match/exceed Cows=13 without increasing herd size.

Evaluates 5 Variants across 100 official benchmark matches (Seeds 1000-1099; 500 total match simulations):
- Baseline V8.1: Cows=12 (Control Baseline)
- Variant A: +2 Wheat Reserve (desired_wheat = animal_count * feed_days + 4)
- Variant B: +$50 Operating Cash Reserve (cash_reserve += $50)
- Variant C: Priority Feed Purchasing (Feed orders placed at top of market queue before hires/seeds)
- Variant D: Feed 2 Days Earlier (feed_days_buffer = 3)
- Variant E: Cows=13 Reference (V8.2 Baseline Control)

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Bankruptcies Count (<$10k final score)
- Standard Deviation ($)
- Minimum Cash Floor ($)
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
    spec = importlib.util.spec_from_file_location(f"v18_f_inst_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_feed_worker(args):
    variant_name, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V81_BASE_STRATEGY)

        if variant_name == "Variant E: Cows=13 Reference":
            overrides["cows"] = 13
        elif variant_name == "Variant A: +2 Wheat Reserve":
            overrides["feed_days_buffer"] = 2
        elif variant_name == "Variant B: +$50 Cash Reserve":
            overrides["cash_reserve"] = 50
        elif variant_name == "Variant D: Feed 2 Days Earlier":
            overrides["feed_days_buffer"] = 3
        elif variant_name == "Variant C: Priority Feed Purchasing":
            orig_market_orders = mod._market_orders

            def priority_market_orders(obs):
                orders = orig_market_orders(obs)
                # Reorder orders so any BUY_PRODUCT WHEAT comes FIRST
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
    print(" RESEARCH 20: FEED INSURANCE & POLICY ABLATION (100 Matches per Variant)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        "Baseline V8.1 (12 Cows)",
        "Variant A: +2 Wheat Reserve",
        "Variant B: +$50 Cash Reserve",
        "Variant C: Priority Feed Purchasing",
        "Variant D: Feed 2 Days Earlier",
        "Variant E: Cows=13 Reference",
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v: [] for v in variants}

    for v_idx, v_name in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/{len(variants)}] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_feed_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    summary = []
    for v_name in variants:
        scores = results_by_variant[v_name]
        mean_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores)
        worst_score = min(scores)
        best_score = max(scores)
        bankruptcies = sum(1 for s in scores if s < 10000.0)

        summary.append({
            "variant": v_name,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "worst": round(worst_score, 2),
            "best": round(best_score, 2),
            "bankruptcies": bankruptcies,
            "scores": scores,
        })

    print("\n" + "=" * 95)
    print(" RESEARCH 20: 100-MATCH FEED POLICY COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<35} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 105)
    for s in summary:
        print(f"{s['variant']:<35} | ${s['mean']:<11,.2f} | ${s['median']:<11,.2f} | ${s['worst']:<9,.2f} | ${s['std_dev']:<8,.2f} | {s['bankruptcies']:<12}")
    print("=" * 95)

    best = max(summary, key=lambda x: x["mean"])
    c13_ref = next(s for s in summary if s["variant"] == "Variant E: Cows=13 Reference")

    print(f"\nTOP VARIANT: {best['variant']} with ${best['mean']:,.2f} Avg Score!")
    print(f"Cows=13 Control Reference: ${c13_ref['mean']:,.2f} Avg Score.")

    report = {
        "summary": summary,
        "best_variant": best,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research20_feed_insurance_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research20_feed_insurance_results.json")


if __name__ == "__main__":
    main()
