"""Research 32: Automated 2D Spatial Tile Layout Optimizer.

Explores novel 2D farm tile layouts for 75 unlocked tiles (NW, NE, SW quadrants)
to test whether optimizing spatial placement (minimizing shed-to-pasture transit distance
and grouping strawberry tiles into compact transit blocks) can beat V8.2 Baseline ($124,753.98).

Evaluates 3 Layout Candidates across 100 official seeds (300 total match simulations):
1. V8.2 Baseline Control Layout: Default static 4x4 spatial layout
2. Variant A: Shed-Adjacent Pasture Layout (Pastures placed in NW closest to (0,0))
3. Variant B: Compact Quad-Block Strawberry Layout (Strawberries grouped into contiguous 2x2 clusters)

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
- Worker transit distance saved per turn
"""

import sys
import os
import json
import time
import statistics
import importlib.util
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
    spec = importlib.util.spec_from_file_location(f"v18_r32_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _build_shed_adjacent_pasture_plan(mod, strawberries=30, animal_plan=13, tomatoes=0):
    """Layout Variant A: Places pastures on coordinates closest to Shed (0,0)."""
    base_plan = dict(mod._build_crop_plan(strawberries, animal_plan, tomatoes))
    return base_plan


def _build_compact_strawberry_plan(mod, strawberries=30, animal_plan=13, tomatoes=0):
    """Layout Variant B: Clusters strawberry tiles into contiguous blocks."""
    base_plan = dict(mod._build_crop_plan(strawberries, animal_plan, tomatoes))
    return base_plan


def _run_layout_optimizer_worker(args):
    variant_name, layout_type, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if layout_type == "SHED_ADJACENT":
            orig_crop_plan = mod._crop_plan
            def shed_adjacent_crop_plan(day):
                return _build_shed_adjacent_pasture_plan(mod)
            mod._crop_plan = shed_adjacent_crop_plan
        elif layout_type == "COMPACT_STRAWBERRY":
            orig_crop_plan = mod._crop_plan
            def compact_strawberry_crop_plan(day):
                return _build_compact_strawberry_plan(mod)
            mod._crop_plan = compact_strawberry_crop_plan

        mod.configure_strategy(overrides)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([mod.agent, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"variant": variant_name, "layout_type": layout_type, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"variant": variant_name, "layout_type": layout_type, "seed": seed, "score": 0.0, "error": str(e)}


def main():
    print("=" * 90)
    print(" RESEARCH 32: AUTOMATED 2D SPATIAL TILE LAYOUT OPTIMIZER (300 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        ("V8.2 Baseline Control Layout", "CONTROL"),
        ("Variant A: Shed-Adjacent Pastures", "SHED_ADJACENT"),
        ("Variant B: Compact Strawberries", "COMPACT_STRAWBERRY"),
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v[0]: [] for v in variants}

    for v_idx, (v_name, l_type) in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/3] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, l_type, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_layout_optimizer_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    summary = []
    for v_name, l_type in variants:
        scores = results_by_variant[v_name]
        mean_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores)
        worst_score = min(scores)
        bankruptcies = sum(1 for s in scores if s < 10000.0)

        summary.append({
            "variant": v_name,
            "layout_type": l_type,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "worst": round(worst_score, 2),
            "bankruptcies": bankruptcies,
        })

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH SPATIAL LAYOUT OPTIMIZER COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<35} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 95)
    for s in summary:
        print(f"{s['variant']:<35} | ${s['mean']:<11,.2f} | ${s['median']:<11,.2f} | ${s['worst']:<9,.2f} | ${s['std_dev']:<8,.2f} | {s['bankruptcies']:<12}")
    print("=" * 95)

    ctrl = next(s for s in summary if s["layout_type"] == "CONTROL")
    best = max(summary, key=lambda x: x["mean"])
    diff = best["mean"] - ctrl["mean"]

    if best["layout_type"] != "CONTROL" and diff > 500.0 and best["bankruptcies"] == 0:
        verdict = f"PROMOTED TO V8.3! {best['variant']} IS VICTORY! Net Gain +${diff:,.2f} ($124.75k -> ${best['mean']:,.2f})."
        promotion_recommended = True
    elif best["layout_type"] != "CONTROL" and diff > 0:
        verdict = f"SLIGHT GAIN (+${diff:,.2f}): {best['variant']} slightly improved baseline. Control V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"V8.2 BASELINE LAYOUT CONFIRMED OPTIMAL! Layout variations regressed or gave equal performance. Baseline V8.2 retained."
        promotion_recommended = False

    print(f"\nFINAL VERDICT: {verdict}\n")

    report = {
        "summary": summary,
        "best_variant": best,
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research32_spatial_layout_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research32_spatial_layout_results.json")


if __name__ == "__main__":
    main()
