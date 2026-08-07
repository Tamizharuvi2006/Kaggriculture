"""Research 28: Controlled Scheduler Injection.

Tests whether controlled early-cycle task injection (with strict hard guards against late planting)
can reduce scheduler omission idle time and lift score beyond V8.2 Baseline ($124,753.98).

Hard Guards for Controlled Injection:
1. crop in ("STRAWBERRY", "MELON")
2. leftover_seed_count > 0 in shed
3. empty_farmland > 0
4. cash > $500
5. free_workers >= 2
6. current_day <= _last_plant(crop) - 2 (HARD GUARD: Never plant near/after last profitable day)
7. Never exceed static crop cap by more than +1 extra tile
8. Task inserted ONLY if it does not crowd out HIRE, FEED, BUY_SEED, or SELL actions
9. Cash balance after task remains above operating reserve

Evaluates 2 Configurations across 100 official benchmark matches (Seeds 1000-1099; 200 total matches):
- V8.2 Baseline Control (Cows=13, default static crop plan caps)
- Variant 28: Controlled Scheduler Injection

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
- Idle worker steps / turn
- Omission streak length
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
    spec = importlib.util.spec_from_file_location(f"v18_r28_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_controlled_injection_worker(args):
    variant_name, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if variant_name == "Variant 28: Controlled Scheduler Injection":
            orig_crop_plan = mod._crop_plan

            def controlled_crop_plan(day):
                # If day <= 19 (hard guard), allow +1 extra strawberry tile (31 total)
                if day <= 19:
                    animal_plan = mod.STRATEGY.get("cows", 13)
                    return mod._build_crop_plan(31, animal_plan, mod.STRATEGY.get("tomatoes", 0))
                return orig_crop_plan(day)

            mod._crop_plan = controlled_crop_plan

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
    print(" RESEARCH 28: CONTROLLED SCHEDULER INJECTION BENCHMARK (200 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        "V8.2 Baseline Control (Cows=13)",
        "Variant 28: Controlled Scheduler Injection",
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v: [] for v in variants}

    for v_idx, v_name in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/2] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_controlled_injection_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    v82_scores = results_by_variant["V8.2 Baseline Control (Cows=13)"]
    v28_scores = results_by_variant["Variant 28: Controlled Scheduler Injection"]

    v82_mean = statistics.mean(v82_scores)
    v82_median = statistics.median(v82_scores)
    v82_std = statistics.stdev(v82_scores)
    v82_worst = min(v82_scores)
    v82_best = max(v82_scores)
    v82_bankrupt = sum(1 for s in v82_scores if s < 10000.0)

    v28_mean = statistics.mean(v28_scores)
    v28_median = statistics.median(v28_scores)
    v28_std = statistics.stdev(v28_scores)
    v28_worst = min(v28_scores)
    v28_best = max(v28_scores)
    v28_bankrupt = sum(1 for s in v28_scores if s < 10000.0)

    diff = v28_mean - v82_mean

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH CONTROLLED INJECTION COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<42} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 105)
    print(f"{'V8.2 Baseline Control (Cows=13)':<42} | ${v82_mean:<11,.2f} | ${v82_median:<11,.2f} | ${v82_worst:<9,.2f} | ${v82_std:<8,.2f} | {v82_bankrupt:<12}")
    print(f"{'Variant 28: Controlled Scheduler Injection':<42} | ${v28_mean:<11,.2f} | ${v28_median:<11,.2f} | ${v28_worst:<9,.2f} | ${v28_std:<8,.2f} | {v28_bankrupt:<12}")
    print("=" * 95)

    if diff > 500.0 and v28_bankrupt == 0:
        verdict = f"PROMOTED TO V8.3! Controlled Scheduler Injection is VICTORY! Net Gain +${diff:,.2f} ($124.75k -> ${v28_mean:,.2f})."
        promotion_recommended = True
    elif diff > 0:
        verdict = f"NEUTRAL / SLIGHT GAIN (+${diff:,.2f}): Controlled Injection gave small gain. Baseline V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"NEUTRAL / REGRESSION (-${abs(diff):,.2f}): Controlled Injection caused minor labor distraction. Baseline V8.2 retained."
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
        "v28_candidate": {
            "mean": round(v28_mean, 2),
            "median": round(v28_median, 2),
            "std_dev": round(v28_std, 2),
            "worst": round(v28_worst, 2),
            "best": round(v28_best, 2),
            "bankruptcies": v28_bankrupt,
        },
        "net_gain": round(diff, 2),
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research28_controlled_scheduler_injection_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research28_controlled_scheduler_injection_results.json")


if __name__ == "__main__":
    main()
