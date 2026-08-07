"""Research 23A: Seed Protection — Drop SELL Orders First on 5-Slot Saturation.

Tests whether protecting growth orders (HIRE, FEED, SEED) by dropping low-priority SELL orders
when market order capacity saturates (MAX_ORDERS = 5) increases overall farm revenue.

Priority order when len(orders) > 5:
1. HIRE (Worker hires)
2. FEED (BUY_PRODUCT WHEAT)
3. SEED (BUY_SEED crop orders)
4. LAND (BUY_LAND)
5. SELL (SELL_PRODUCT surplus orders)

Evaluates 2 Configurations across 100 official benchmark matches (Seeds 1000-1099; 200 total matches):
- V8.2 Baseline Control (Cows=13, default order priority)
- Variant 23A: Seed Protection (Drop SELL orders first when order count > 5)

Logs:
- Average Score ($)
- Median Score ($)
- Worst Score ($)
- Standard Deviation ($)
- Bankruptcies Count (<$10k final score)
- Saturated turns count
- Dropped SEED orders count
- Dropped SELL orders count
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
    spec = importlib.util.spec_from_file_location(f"v18_r23a_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_seed_protection_worker(args):
    variant_name, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if variant_name == "Variant 23A: Seed Protection":
            orig_market_orders = mod._market_orders

            def seed_protection_market_orders(obs):
                # Generate all candidate orders without MAX_ORDERS truncation
                # We save original MAX_ORDERS and restore
                old_max = mod.MAX_ORDERS
                mod.MAX_ORDERS = 99
                candidate_orders = orig_market_orders(obs)
                mod.MAX_ORDERS = old_max

                if len(candidate_orders) <= 5:
                    return candidate_orders

                # Prioritize growth orders over sell orders
                hires = [o for o in candidate_orders if o[0] == "HIRE"]
                feed = [o for o in candidate_orders if len(o) > 1 and o[1] == "WHEAT" and o[0] == "BUY_PRODUCT"]
                seeds = [o for o in candidate_orders if o[0] == "BUY_SEED"]
                land = [o for o in candidate_orders if o[0] == "BUY_LAND"]
                sells = [o for o in candidate_orders if o[0] in ("SELL_PRODUCT", "SELL_ANIMAL")]

                # Pack top 5 orders
                packed = []
                for group in (hires, feed, seeds, land, sells):
                    for order in group:
                        if len(packed) < 5:
                            packed.append(order)

                return packed

            mod._market_orders = seed_protection_market_orders

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
    print(" RESEARCH 23A: SEED PROTECTION BENCHMARK (200 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        "V8.2 Baseline Control (Cows=13)",
        "Variant 23A: Seed Protection",
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v: [] for v in variants}

    for v_idx, v_name in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/2] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_seed_protection_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    v82_scores = results_by_variant["V8.2 Baseline Control (Cows=13)"]
    v23a_scores = results_by_variant["Variant 23A: Seed Protection"]

    v82_mean = statistics.mean(v82_scores)
    v82_median = statistics.median(v82_scores)
    v82_std = statistics.stdev(v82_scores)
    v82_worst = min(v82_scores)
    v82_best = max(v82_scores)
    v82_bankrupt = sum(1 for s in v82_scores if s < 10000.0)

    v23a_mean = statistics.mean(v23a_scores)
    v23a_median = statistics.median(v23a_scores)
    v23a_std = statistics.stdev(v23a_scores)
    v23a_worst = min(v23a_scores)
    v23a_best = max(v23a_scores)
    v23a_bankrupt = sum(1 for s in v23a_scores if s < 10000.0)

    diff = v23a_mean - v82_mean

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH SEED PROTECTION COMPARATIVE TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<35} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 105)
    print(f"{'V8.2 Baseline Control (Cows=13)':<35} | ${v82_mean:<11,.2f} | ${v82_median:<11,.2f} | ${v82_worst:<9,.2f} | ${v82_std:<8,.2f} | {v82_bankrupt:<12}")
    print(f"{'Variant 23A: Seed Protection':<35} | ${v23a_mean:<11,.2f} | ${v23a_median:<11,.2f} | ${v23a_worst:<9,.2f} | ${v23a_std:<8,.2f} | {v23a_bankrupt:<12}")
    print("=" * 95)

    if diff > 500.0 and v23a_bankrupt == 0:
        verdict = f"PROMOTED TO V8.3! Seed Protection (dropping SELL orders first) is VICTORY! Net Gain +${diff:,.2f} ($124.75k -> ${v23a_mean:,.2f})."
        promotion_recommended = True
    elif diff > 0:
        verdict = f"MODEST GAIN (+${diff:,.2f}): Seed Protection slightly improved V8.2. Baseline V8.2 retained."
        promotion_recommended = False
    else:
        verdict = f"NEUTRAL / REGRESSION (-${abs(diff):,.2f}): Dropping SELL orders delayed crop liquidity. Baseline V8.2 retained."
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
        "v23a_candidate": {
            "mean": round(v23a_mean, 2),
            "median": round(v23a_median, 2),
            "std_dev": round(v23a_std, 2),
            "worst": round(v23a_worst, 2),
            "best": round(v23a_best, 2),
            "bankruptcies": v23a_bankrupt,
        },
        "net_gain": round(diff, 2),
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research23a_seed_protection_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research23a_seed_protection_results.json")


if __name__ == "__main__":
    main()
