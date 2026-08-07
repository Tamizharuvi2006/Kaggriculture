"""Research 23B: Saturated-Turn Sell Importance Audit.

Audits every market order on 5-slot saturated turns across 100 official matches (Seeds 1000-1099; 4,639 saturated turns).

Ranks sell order categories by:
1. Product type (STRAWBERRY, MELON, CARROT, WHEAT, FERTILIZER)
2. Frequency of occurrence on saturated turns
3. Immediate cash generated ($)
4. Unit price ($/item)
5. Importance ranking & potential for safe deferral to unblock growth orders
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
    spec = importlib.util.spec_from_file_location(f"v18_r23b_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_saturated_sell_orders(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    saturated_turns_count = 0
    sell_order_stats = {}

    def tracking_agent(obs):
        nonlocal saturated_turns_count

        action_dict = mod.agent(obs)
        orders = action_dict.get("market", [])

        if len(orders) >= 5:
            saturated_turns_count += 1

            for o in orders:
                if o[0] == "SELL":
                    prod = o[1] if len(o) > 1 else "UNKNOWN"
                    qty = int(o[2]) if len(o) > 2 else 1

                    prices = mod._get(obs, "market_prices", {}) or {}
                    unit_price = float(prices.get(prod, 15.0)) if isinstance(prices, dict) else 15.0
                    cash_gen = qty * unit_price

                    if prod not in sell_order_stats:
                        sell_order_stats[prod] = {
                            "count": 0,
                            "total_qty": 0,
                            "total_cash": 0.0,
                            "unit_prices": [],
                        }

                    sell_order_stats[prod]["count"] += 1
                    sell_order_stats[prod]["total_qty"] += qty
                    sell_order_stats[prod]["total_cash"] += cash_gen
                    sell_order_stats[prod]["unit_prices"].append(unit_price)

        return action_dict

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])

    return {
        "seed": seed,
        "score": final_score,
        "saturated_turns": saturated_turns_count,
        "sell_stats": sell_order_stats,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 23B: SATURATED-TURN SELL IMPORTANCE AUDIT (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing saturated sell orders across {len(seeds)} official seeds...")

    tasks = [(seed, seed) for seed in seeds]
    results = []

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_saturated_sell_orders, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Aggregate global product sell statistics across all saturated turns
    total_saturated_turns = sum(r["saturated_turns"] for r in results)

    global_prod_stats = {}
    for r in results:
        for prod, p_stat in r["sell_stats"].items():
            if prod not in global_prod_stats:
                global_prod_stats[prod] = {
                    "occurrences": 0,
                    "total_units_sold": 0,
                    "total_cash_generated": 0.0,
                    "prices": [],
                }
            global_prod_stats[prod]["occurrences"] += p_stat["count"]
            global_prod_stats[prod]["total_units_sold"] += p_stat["total_qty"]
            global_prod_stats[prod]["total_cash_generated"] += p_stat["total_cash"]
            global_prod_stats[prod]["prices"].extend(p_stat["unit_prices"])

    # Rank products by average cash generated per order
    ranked_products = []
    for prod, data in global_prod_stats.items():
        occ = data["occurrences"]
        avg_cash = data["total_cash_generated"] / max(1, occ)
        avg_price = statistics.mean(data["prices"]) if data["prices"] else 0.0
        pct_turns = (occ / max(1, total_saturated_turns)) * 100.0

        ranked_products.append({
            "product": prod,
            "occurrences": occ,
            "pct_of_saturated_turns": round(pct_turns, 2),
            "total_units_sold": data["total_units_sold"],
            "total_cash_generated": round(data["total_cash_generated"], 2),
            "avg_cash_per_order": round(avg_cash, 2),
            "avg_unit_price": round(avg_price, 2),
        })

    # Sort descending by avg cash per order
    ranked_products.sort(key=lambda x: x["avg_cash_per_order"], reverse=True)

    print("\n" + "=" * 100)
    print(" SATURATED-TURN SELL ORDER IMPORTANCE RANKING")
    print("=" * 100)
    print(f"{'Rank':<5} | {'Product Name':<15} | {'Occurrences':<12} | {'% Sat Turns':<12} | {'Avg Cash/Order ($)':<20} | {'Avg Unit Price ($)':<18}")
    print("-" * 100)
    for idx, p in enumerate(ranked_products, 1):
        print(f"{idx:<5} | {p['product']:<15} | {p['occurrences']:<12} | {p['pct_of_saturated_turns']:<11}% | ${p['avg_cash_per_order']:<19,.2f} | ${p['avg_unit_price']:<17,.2f}")
    print("=" * 100)

    # Classify critical vs deferrable sells
    print("\nCLASSIFICATION & DEFERRAL POTENTIAL:")
    critical = [p["product"] for p in ranked_products if p["avg_cash_per_order"] > 100.0]
    deferrable = [p["product"] for p in ranked_products if p["avg_cash_per_order"] <= 100.0]

    print(f" CRITICAL LIQUIDITY SELLS (Avg Cash > $100):   {critical}")
    print(f" DEFERRABLE / LOW-IMPACT SELLS (Avg Cash <= $100): {deferrable}")

    report = {
        "total_saturated_turns": total_saturated_turns,
        "product_importance_ranking": ranked_products,
        "critical_products": critical,
        "deferrable_products": deferrable,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research23b_sell_importance_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full report to research23b_sell_importance_results.json")


if __name__ == "__main__":
    main()
