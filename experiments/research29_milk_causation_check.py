"""Research 29 Diagnostic: Milk Causation Check.

Computes explicit Pearson correlations across 100 official benchmark seeds:
1. corr(score, average_milk_price)
2. corr(score, total_milk_units_sold)
3. corr(score, milk_revenue_share_percentage)

Tests whether Cow #13 wins because of Milk price spikes (causation) vs Milk volume/revenue share.
"""

import sys
import os
import json
import time
import math
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
    spec = importlib.util.spec_from_file_location(f"v18_r29c_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_milk_causation_seed(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    milk_prices = []
    total_milk_sold = 0.0
    total_milk_rev = 0.0
    total_gross_rev = 0.0

    def tracking_agent(obs):
        nonlocal total_milk_sold, total_milk_rev, total_gross_rev

        market = mod._get(obs, "market", {}) or {}
        prices = mod._get(market, "prices", {}) or {}

        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)
        if milk_p > 0:
            milk_prices.append(milk_p)

        action_dict = mod.agent(obs)

        # Track executed market sell orders
        for order in action_dict.get("market", []):
            if order and order[0] == "SELL":
                item = order[1] if len(order) > 1 else None
                qty = float(order[2]) if len(order) > 2 else 1.0
                prod_p_data = prices.get(item, 0.0)
                item_p = float(prod_p_data.get("price", 0.0) if isinstance(prod_p_data, dict) else prod_p_data or 0.0)
                rev = qty * item_p

                total_gross_rev += rev
                if item == "MILK":
                    total_milk_sold += qty
                    total_milk_rev += rev

        return action_dict

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])
    avg_milk_price = statistics.mean(milk_prices) if milk_prices else 0.0
    milk_rev_share = (total_milk_rev / max(1.0, total_gross_rev)) * 100.0

    return {
        "seed": seed,
        "score": final_score,
        "avg_milk_price": avg_milk_price,
        "total_milk_sold": total_milk_sold,
        "total_milk_rev": total_milk_rev,
        "milk_rev_share": milk_rev_share,
    }


def pearson_corr(x, y):
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = math.sqrt(sum((xi - mean_x)**2 for xi in x) * sum((yi - mean_y)**2 for yi in y))
    return num / max(1e-9, den)


def main():
    print("=" * 90)
    print(" RESEARCH 29 DIAGNOSTIC: MILK CAUSATION CHECK (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_milk_causation_seed, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    scores = [r["score"] for r in results]
    avg_milk_prices = [r["avg_milk_price"] for r in results]
    total_milk_solds = [r["total_milk_sold"] for r in results]
    milk_rev_shares = [r["milk_rev_share"] for r in results]

    corr_price = pearson_corr(scores, avg_milk_prices)
    corr_volume = pearson_corr(scores, total_milk_solds)
    corr_share = pearson_corr(scores, milk_rev_shares)

    print("\n" + "=" * 90)
    print(" MILK CAUSATION PEARSON CORRELATION MATRIX (100 Benchmark Seeds)")
    print("=" * 90)
    print(f" Average Score:                      ${statistics.mean(scores):,.2f}")
    print(f" Average Milk Price:                ${statistics.mean(avg_milk_prices):.2f}/unit")
    print(f" Average Total Milk Sold:           {statistics.mean(total_milk_solds):.1f} units")
    print(f" Average Milk Revenue Share:        {statistics.mean(milk_rev_shares):.2f}% of total farm revenue")
    print("-" * 90)
    print(f" 1. corr(score, avg_milk_price):    {corr_price:<+7.3f}")
    print(f" 2. corr(score, total_milk_sold):   {corr_volume:<+7.3f}")
    print(f" 3. corr(score, milk_rev_share):   {corr_share:<+7.3f}")
    print("=" * 90)

    report = {
        "mean_score": round(statistics.mean(scores), 2),
        "mean_milk_price": round(statistics.mean(avg_milk_prices), 2),
        "mean_milk_sold": round(statistics.mean(total_milk_solds), 2),
        "mean_milk_rev_share": round(statistics.mean(milk_rev_shares), 2),
        "corr_score_vs_milk_price": round(corr_price, 3),
        "corr_score_vs_milk_volume": round(corr_volume, 3),
        "corr_score_vs_milk_rev_share": round(corr_share, 3),
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research29_milk_causation_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research29_milk_causation_results.json")


if __name__ == "__main__":
    main()
