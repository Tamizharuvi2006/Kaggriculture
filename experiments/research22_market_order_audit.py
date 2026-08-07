"""Research 22: Market Order Bottleneck Audit.

Audits market order slot utilization, slot saturation, and order truncation (MAX_ORDERS = 5) in V8.2 Baseline across 100 official matches (Seeds 1000-1099; 72,000 game turns).

Logs:
- Average unused market order slots per turn
- Total omitted / truncated profitable market orders (feed, seeds, hires, animals)
- Category breakdown of order rejections due to MAX_ORDERS cap
- Most common order rejection reason
- Correlation between order slot saturation and final match score
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
    spec = importlib.util.spec_from_file_location(f"v18_audit_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def audit_seed_market_orders(seed, process_id):
    mod = _load_v18_module(process_id)
    mod.configure_strategy(dict(V82_BASE_STRATEGY))

    turns_evaluated = 0
    orders_issued_count = 0
    unused_slots_count = 0
    saturated_turns_count = 0  # Turns where len(orders) == 5

    omitted_orders = {
        "feed": 0,
        "seeds": 0,
        "hires": 0,
        "animals": 0,
        "sell": 0,
    }

    def tracking_agent(obs):
        nonlocal turns_evaluated, orders_issued_count, unused_slots_count, saturated_turns_count

        turns_evaluated += 1

        player = int(mod._get(obs, "player", 0))
        farm = mod._get(obs, "farms", [])[player]
        private = mod._get(obs, "private", {}) or {}
        tiles = mod._get(farm, "tiles", [])
        money = float(mod._get(farm, "money", 0))
        day = int(mod._get(obs, "day", 0))
        unlocked = set(mod._get(farm, "unlocked_quadrants", ["NW"]) or ["NW"])

        # Track actual market orders issued by baseline agent
        action_dict = mod.agent(obs)
        actual_orders = action_dict.get("market", [])
        num_orders = len(actual_orders)

        orders_issued_count += num_orders
        unused_slots_count += max(0, 5 - num_orders)

        if num_orders >= 5:
            saturated_turns_count += 1

            # Inspect if profitable orders were omitted due to 5-slot truncation
            # 1. Seeds check: empty tiles exist and money > operating reserve, but 0 seed orders in actual_orders
            empty_tiles = sum(
                1 for y in range(len(tiles)) for x in range(len(tiles[y]))
                if mod._active_target((x, y), day, unlocked) and tiles[y][x] is None
            )
            has_seed_order = any(o[0] == "BUY_SEED" for o in actual_orders)
            if empty_tiles > 0 and money > 150.0 and not has_seed_order:
                omitted_orders["seeds"] += 1

            # 2. Feed check: feed deficit exists but no BUY_PRODUCT WHEAT order
            has_feed_order = any(len(o) > 1 and o[1] == "WHEAT" and o[0] == "BUY_PRODUCT" for o in actual_orders)
            shed_w = int(private.get("shed", {}).get("WHEAT", 0))
            if shed_w < 5 and money > 50.0 and not has_feed_order:
                omitted_orders["feed"] += 1

            # 3. Hires check: hiring target not met but no HIRE order
            has_hire_order = any(o[0] == "HIRE" for o in actual_orders)
            hires_today = int(farm.get("hires_today", 0))
            hire_target = mod._hire_target(day)
            if hires_today < hire_target and money > 100.0 and not has_hire_order:
                omitted_orders["hires"] += 1

        return action_dict

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state = env.run([tracking_agent, _noop_agent])

    final_score = float(state[-1][0]["reward"])

    return {
        "seed": seed,
        "score": final_score,
        "turns_evaluated": turns_evaluated,
        "orders_issued": orders_issued_count,
        "unused_slots": unused_slots_count,
        "saturated_turns": saturated_turns_count,
        "omitted_orders": omitted_orders,
    }


def main():
    print("=" * 90)
    print(" RESEARCH 22: MARKET ORDER BOTTLENECK AUDIT (100 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    max_workers = 4
    start_time = time.time()

    print(f"Auditing market orders across {len(seeds)} official seeds using {max_workers} CPU cores...")

    seed_results = []
    tasks = [(seed, seed) for seed in seeds]

    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(audit_seed_market_orders, s, pid): s for s, pid in tasks}
        for future in as_completed(futures):
            res = future.result()
            seed_results.append(res)
            completed += 1
            if completed % 25 == 0 or completed == len(seeds):
                print(f"  [Progress {completed}/100 seeds audited] Elapsed: {time.time()-start_time:.1f}s")

    elapsed = time.time() - start_time

    # Aggregate global statistics
    total_turns = sum(r["turns_evaluated"] for r in seed_results)
    total_orders = sum(r["orders_issued"] for r in seed_results)
    total_unused = sum(r["unused_slots"] for r in seed_results)
    total_saturated = sum(r["saturated_turns"] for r in seed_results)

    total_omitted = {
        "seeds": sum(r["omitted_orders"]["seeds"] for r in seed_results),
        "feed": sum(r["omitted_orders"]["feed"] for r in seed_results),
        "hires": sum(r["omitted_orders"]["hires"] for r in seed_results),
    }

    avg_unused_per_turn = total_unused / max(1, total_turns)
    avg_orders_per_turn = total_orders / max(1, total_turns)
    saturated_pct = (total_saturated / max(1, total_turns)) * 100.0

    # Correlation between saturated turns and final score
    scores = [r["score"] for r in seed_results]
    sat_turns = [r["saturated_turns"] for r in seed_results]

    mean_score = statistics.mean(scores)
    mean_sat = statistics.mean(sat_turns)

    # Pearson correlation coefficient
    num = sum((s - mean_score) * (st - mean_sat) for s, st in zip(scores, sat_turns))
    den = math.sqrt(sum((s - mean_score)**2 for s in scores) * sum((st - mean_sat)**2 for st in sat_turns))
    corr = num / max(1e-9, den)

    print("\n" + "=" * 90)
    print(" MARKET ORDER BOTTLENECK AUDIT RESULTS")
    print("=" * 90)
    print(f" Total Game Turns Audited:         {total_turns}")
    print(f" Total Market Orders Issued:       {total_orders} ({avg_orders_per_turn:.2f} orders/turn)")
    print(f" Avg Unused Order Slots / Turn:    {avg_unused_per_turn:.2f} / 5 slots")
    print(f" 5-Slot Saturated Turns:           {total_saturated} ({saturated_pct:.2f}% of all turns)")
    print("-" * 90)
    print(" OMITTED PROFITABLE ORDERS DUE TO 5-SLOT TRUNCATION:")
    for cat, cnt in sorted(total_omitted.items(), key=lambda x: x[1], reverse=True):
        print(f"   - Omitted {cat.upper():<8} Orders: {cnt} turns ({cnt/total_turns*100:.2f}% of all turns)")
    print("-" * 90)
    print(f" Correlation (Saturated Turns vs Score): {corr:.3f}")
    print("=" * 90)

    most_omitted_cat = max(total_omitted, key=total_omitted.get)

    report = {
        "total_turns_audited": total_turns,
        "total_orders_issued": total_orders,
        "avg_orders_per_turn": round(avg_orders_per_turn, 2),
        "avg_unused_slots_per_turn": round(avg_unused_per_turn, 2),
        "total_5slot_saturated_turns": total_saturated,
        "saturated_turns_percentage": round(saturated_pct, 2),
        "omitted_orders_breakdown": total_omitted,
        "most_common_omitted_category": most_omitted_cat,
        "correlation_saturated_turns_vs_score": round(corr, 3),
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research22_market_order_audit_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research22_market_order_audit_results.json")


if __name__ == "__main__":
    import math
    main()
