"""Research 29: Opponent Market Audit.

Audits turn-by-turn market price dynamics, price curves, volatility, and sell windows
across 100 official benchmark matches (Seeds 1000-1099; 71,900 game turns).

Logs & Measures:
1. Turn-by-turn price curves for MILK, STRAWBERRY, MELON, WHEAT, CARROT, FERTILIZER
2. Volatility (StdDev) of market prices per product
3. Price curve comparison: High-Scoring Matches (Top 10%) vs Low-Scoring Matches (Bottom 10%)
4. Impact of Milk daily steady cash flow vs market price spikes
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
    spec = importlib.util.spec_from_file_location(f"v18_r29_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_opponent_market_seed(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    price_history = {
        "MILK": [],
        "STRAWBERRY": [],
        "MELON": [],
        "WHEAT": [],
        "CARROT": [],
        "FERTILIZER": [],
    }

    def tracking_agent(obs):
        market = mod._get(obs, "market", {}) or {}
        prices = mod._get(market, "prices", {}) or {}
        
        # Log market sell prices per product
        for prod in price_history.keys():
            prod_data = prices.get(prod, 0.0)
            if isinstance(prod_data, dict):
                price = float(prod_data.get("price", 0.0))
            else:
                price = float(prod_data or 0.0)
            price_history[prod].append(price)

        return mod.agent(obs)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])

    return {
        "seed": seed,
        "score": final_score,
        "price_history": price_history,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 29: OPPONENT MARKET AUDIT & PRICE VOLATILITY (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing market price trajectories across {len(seeds)} official seeds...")

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_opponent_market_seed, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Sort results by score to compare top 10% vs bottom 10%
    results.sort(key=lambda r: r["score"], reverse=True)
    top_10 = results[:10]
    bottom_10 = results[-10:]

    scores = [r["score"] for r in results]
    mean_score = statistics.mean(scores)

    # Compute global price statistics
    products = ["MILK", "STRAWBERRY", "MELON", "WHEAT", "CARROT", "FERTILIZER"]
    market_stats = {}

    for prod in products:
        all_prices = []
        for r in results:
            all_prices.extend(r["price_history"][prod])

        top_prices = []
        for r in top_10:
            top_prices.extend(r["price_history"][prod])

        bot_prices = []
        for r in bottom_10:
            bot_prices.extend(r["price_history"][prod])

        mean_p = statistics.mean(all_prices) if all_prices else 0.0
        std_p = statistics.stdev(all_prices) if len(all_prices) > 1 else 0.0
        top_mean_p = statistics.mean(top_prices) if top_prices else 0.0
        bot_mean_p = statistics.mean(bot_prices) if bot_prices else 0.0

        market_stats[prod] = {
            "mean_price": round(mean_p, 2),
            "std_dev_price": round(std_p, 2),
            "top_10_avg_price": round(top_mean_p, 2),
            "bottom_10_avg_price": round(bot_mean_p, 2),
            "price_delta": round(top_mean_p - bot_mean_p, 2),
        }

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH MARKET AUDIT TABLE")
    print("=" * 95)
    print(f"{'Product':<15} | {'Avg Price ($)':<14} | {'Volatility (StdDev)':<20} | {'Top 10% Avg ($)':<15} | {'Bottom 10% Avg ($)':<18}")
    print("-" * 95)
    for prod, s in market_stats.items():
        print(f"{prod:<15} | ${s['mean_price']:<13.2f} | ${s['std_dev_price']:<19.2f} | ${s['top_10_avg_price']:<14.2f} | ${s['bottom_10_avg_price']:<17.2f}")
    print("=" * 95)

    report = {
        "mean_score": round(mean_score, 2),
        "top_10_avg_score": round(statistics.mean([r["score"] for r in top_10]), 2),
        "bottom_10_avg_score": round(statistics.mean([r["score"] for r in bottom_10]), 2),
        "market_stats": market_stats,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research29_opponent_market_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research29_opponent_market_results.json")


if __name__ == "__main__":
    main()
