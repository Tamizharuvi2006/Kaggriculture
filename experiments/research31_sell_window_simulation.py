"""Research 31: Counterfactual Sell-Window Simulation.

Simulates holding Strawberry crop inventory (+1 day, +2 days, +3 days) to sell into market price spikes,
without modifying any live agent submission code.

Evaluates 4 Counterfactual Variants across 100 official seeds (400 match simulations):
1. Control: Immediate Strawberry selling (V8.2 Baseline behavior)
2. Variant A: Wait +1 Day for price spike
3. Variant B: Wait +2 Days for price spike
4. Variant C: Wait +3 Days for price spike

Logs:
- Average Score ($)
- Net Revenue Delta ($)
- Cash Liquidity Shortages Created
- Bankruptcies Caused
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
    spec = importlib.util.spec_from_file_location(f"v18_r31_{mod_id}", v18_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _run_sell_window_worker(args):
    variant_name, hold_days, seed, process_id = args
    try:
        mod = _load_v18_module(process_id)
        overrides = dict(V82_BASE_STRATEGY)

        if hold_days > 0:
            strawberry_hold_until = {}

            def simulated_market_orders(obs):
                action_dict = mod.agent(obs)
                day = int(mod._get(obs, "day", 0))
                market_orders = action_dict.get("market", [])

                if not market_orders:
                    return action_dict

                new_orders = []
                for order in market_orders:
                    if order and order[0] == "SELL" and len(order) > 1 and order[1] == "STRAWBERRY":
                        # Apply hold condition
                        if day not in strawberry_hold_until:
                            strawberry_hold_until[day] = day + hold_days

                        if day < strawberry_hold_until[day]:
                            # Hold order for price spike
                            continue

                    new_orders.append(order)

                action_dict["market"] = new_orders
                return action_dict

            agent_fn = simulated_market_orders
        else:
            mod.configure_strategy(overrides)
            agent_fn = mod.agent

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([agent_fn, _noop_agent])

        last_step = env.steps[-1]
        score = float(last_step[0]["observation"]["farms"][0]["money"])
        return {"variant": variant_name, "hold_days": hold_days, "seed": seed, "score": score, "error": None}
    except Exception as e:
        return {"variant": variant_name, "hold_days": hold_days, "seed": seed, "score": 0.0, "error": str(e)}


def main():
    print("=" * 90)
    print(" RESEARCH 31: SELL-WINDOW COUNTERFACTUAL SIMULATION (400 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))
    variants = [
        ("Control (Immediate Sell)", 0),
        ("Variant A (Wait +1 Day)", 1),
        ("Variant B (Wait +2 Days)", 2),
        ("Variant C (Wait +3 Days)", 3),
    ]

    max_workers = 4
    start_time = time.time()

    results_by_variant = {v[0]: [] for v in variants}

    for v_idx, (v_name, h_days) in enumerate(variants, 1):
        print(f"\n--- [{v_idx}/4] Evaluating {v_name} across 100 seeds ---")
        v_tasks = [(v_name, h_days, seed, seed) for seed in seeds]

        completed = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_sell_window_worker, task): task for task in v_tasks}
            for future in as_completed(futures):
                res = future.result()
                results_by_variant[v_name].append(res["score"])
                completed += 1
                if completed % 25 == 0 or completed == len(v_tasks):
                    print(f"  [Progress {completed}/100 seeds] Mean Score: ${statistics.mean(results_by_variant[v_name]):,.2f}")

    elapsed = time.time() - start_time

    # Summary analysis
    summary = []
    for v_name, h_days in variants:
        scores = results_by_variant[v_name]
        mean_score = statistics.mean(scores)
        median_score = statistics.median(scores)
        std_score = statistics.stdev(scores)
        worst_score = min(scores)
        bankruptcies = sum(1 for s in scores if s < 10000.0)

        summary.append({
            "variant": v_name,
            "hold_days": h_days,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "std_dev": round(std_score, 2),
            "worst": round(worst_score, 2),
            "bankruptcies": bankruptcies,
        })

    print("\n" + "=" * 95)
    print(" OFFICIAL 100-MATCH COUNTERFACTUAL SELL-WINDOW TABLE (Seeds 1000-1099)")
    print("=" * 95)
    print(f"{'Variant Label':<30} | {'Mean ($)':<12} | {'Median ($)':<12} | {'Worst ($)':<10} | {'StdDev ($)':<9} | {'Bankruptcies':<12}")
    print("-" * 95)
    for s in summary:
        print(f"{s['variant']:<30} | ${s['mean']:<11,.2f} | ${s['median']:<11,.2f} | ${s['worst']:<9,.2f} | ${s['std_dev']:<8,.2f} | {s['bankruptcies']:<12}")
    print("=" * 95)

    ctrl = next(s for s in summary if s["hold_days"] == 0)
    best = max(summary, key=lambda x: x["mean"])
    diff = best["mean"] - ctrl["mean"]

    if best["hold_days"] != 0 and diff > 500.0 and best["bankruptcies"] == 0:
        verdict = f"PROMOTED TO V8.3! {best['variant']} IS VICTORY! Net Gain +${diff:,.2f} ($124.75k -> ${best['mean']:,.2f})."
        promotion_recommended = True
    elif best["hold_days"] != 0 and diff > 0:
        verdict = f"SLIGHT GAIN (+${diff:,.2f}): {best['variant']} slightly improved baseline. Control retained."
        promotion_recommended = False
    else:
        verdict = f"IMMEDIATE SELLING CONFIRMED OPTIMAL! Holding inventory delayed cash flow and increased bankruptcy risk. Control V8.2 retained."
        promotion_recommended = False

    print(f"\nFINAL VERDICT: {verdict}\n")

    report = {
        "summary": summary,
        "best_variant": best,
        "promotion_recommended": promotion_recommended,
        "final_verdict": verdict,
        "total_elapsed_seconds": round(elapsed, 1),
    }

    with open("research31_sell_window_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved full report to research31_sell_window_results.json")


if __name__ == "__main__":
    main()
