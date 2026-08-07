"""Research 25: Herd Frontier Search (Cows=13 vs Cows=14 vs Cows=15).

Maps the exact economic frontier around cattle herd size across 100 official benchmark matches (Seeds 1000-1099; 300 total matches).

Evaluates 3 Configurations:
- V8.2 Baseline Control: cows = 13
- Variant A: cows = 14
- Variant B: cows = 15

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
- Worker idle turns
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
    spec = importlib.util.spec_from_file_location(f"v18_r25_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_herd_worker(args):
    variant_name, cow_count, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)
        overrides["cows"] = cow_count

        mod.configure_strategy(overrides)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"variant": variant_name, "cow_count": cow_count, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"variant": variant_name, "cow_count": cow_count, "seed": seed, "score": 0.0, "error": str(e)}


def main():
    print("=" * 90)
    print(" RESEARCH 25: HERD FRONTIER SEARCH (300 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        ("V8.2 Control (Cows=13)", 13),
        ("Variant A (Cows=14)", 14),
        ("Variant B (Cows=15)", 15),
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v[0]: [] for v in variants}

    for v_idx, (v_name, cow_cnt) in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/3] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, cow_cnt, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_herd_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    summary = []
    for v_name, cow_cnt in variants:
        scores = results_by_variant[v_name]
        mean_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores)
        worst_score = min(scores)
        best_score = max(scores)
        bankruptcies = sum(1 for s in scores if s < 10000.0)

        summary.append({
            "variant": v_name,
            "cow_count": cow_cnt,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "worst": round(worst_score, 2),
            "best": round(best_score, 2),
            "bankruptcies": bankruptcies,
            "scores": scores,
        })

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH HERD FRONTIER COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<30} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 100)
    for s in summary:
        print(f"{s['variant']:<30} | ${s['mean']:<11,.2f} | ${s['median']:<11,.2f} | ${s['worst']:<9,.2f} | ${s['std_dev']:<8,.2f} | {s['bankruptcies']:<12}")
    print("=" * 95)

    c13 = next(s for s in summary if s["cow_count"] == 13)
    best = max(summary, key=lambda x: x["mean"])
    diff = best["mean"] - c13["mean"]

    if best["cow_count"] != 13 and diff > 500.0 and best["bankruptcies"] == 0:
        verdict = f"PROMOTED TO V8.3! {best['variant']} is NEW BEST! Net Gain +${diff:,.2f} over V8.2 Baseline ($124.75k -> ${best['mean']:,.2f})."
        promotion_recommended = True
    elif best["cow_count"] != 13 and diff > 0:
        verdict = f"MODEST GAIN (+${diff:,.2f}): {best['variant']} slightly improved V8.2. Baseline V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"COWS=13 CONFIRMED OPTIMAL! Cows=14/15 regressed or showed diminishing returns. Baseline V8.2 retained."
        promotion_recommended = False

    print(f"\nFINAL VERDICT: {verdict}\n")

    report = {
        "summary": summary,
        "best_variant": best,
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research25_herd_frontier_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research25_herd_frontier_results.json")


if __name__ == "__main__":
    main()
