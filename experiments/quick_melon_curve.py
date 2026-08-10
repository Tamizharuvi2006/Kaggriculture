"""Fast Melon Opening Fine-Tuning Benchmark (10 vs 11 vs 12 Melons across 150 Matches).

Fast evaluation across Seeds 1000-1049 (50 matches per variant vs V4.1 Master Champion):
- P2A: 10 Opening Melons + Cash Reserve
- P2B: 11 Opening Melons + Cash Reserve
- P2C: 12 Opening Melons + Cash Reserve
"""

import sys
import os
import json
import statistics
import importlib.util
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_melon_variant(melon_count, process_id):
    spec = importlib.util.spec_from_file_location(f"q_melon_{melon_count}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if melon_count == "V41":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": int(melon_count),
        "cows": 8,
    })

    _base = mod.agent

    def agent_wrapper(obs, configuration=None):
        action_dict = _base(obs)
        market_orders = action_dict.get("market", [])
        if not market_orders or len(market_orders) <= 1:
            return action_dict

        prices = mod._get(mod._get(obs, "market", {}), "prices", {}) or {}
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

        def order_priority(idx_order):
            idx, ord_item = idx_order
            if not ord_item or ord_item[0] != "SELL":
                return (10, idx)
            item = ord_item[1] if len(ord_item) > 1 else ""
            if item == "MILK" and milk_p >= 230.0:
                return (0, idx)
            elif item == "MELON":
                return (1, idx)
            elif item == "STRAWBERRY":
                return (2, idx)
            elif item == "WHEAT":
                return (3, idx)
            return (4, idx)

        reordered = [ord_item for _, ord_item in sorted(enumerate(market_orders), key=order_priority)]
        action_dict["market"] = reordered
        return action_dict

    return agent_wrapper


def _run_melon_match(args):
    melon_count, seed, process_id = args
    try:
        agent_var = _load_melon_variant(melon_count, f"{process_id}_var")
        agent_v41 = _load_melon_variant("V41", f"{process_id}_v41")

        p0_is_var = (seed % 2 == 0)
        p0 = agent_var if p0_is_var else agent_v41
        p1 = agent_v41 if p0_is_var else agent_var

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([p0, p1])

        idx_var = 0 if p0_is_var else 1
        idx_v41 = 1 if p0_is_var else 0

        d8_cash = float(state_history[191][idx_var]["observation"]["farms"][idx_var]["money"])
        d15_cash = float(state_history[359][idx_var]["observation"]["farms"][idx_var]["money"])
        final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
        final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

        return {
            "melon_count": melon_count,
            "seed": seed,
            "d8_cash": d8_cash,
            "d15_cash": d15_cash,
            "final_cash": final_cash,
            "final_v41": final_v41,
            "win": final_cash > final_v41,
            "error": None,
        }
    except Exception as e:
        return {
            "melon_count": melon_count,
            "seed": seed,
            "d8_cash": 0.0,
            "d15_cash": 0.0,
            "final_cash": 0.0,
            "final_v41": 0.0,
            "win": False,
            "error": str(e),
        }


def main():
    print("=" * 90)
    print(" FAST MELON OPENING CURVE BENCHMARK: 10 vs 11 vs 12 MELONS (150 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1050))
    results_by_count = {}

    for count in [10, 11, 12]:
        tasks = [(count, seed, f"qm_{count}_{seed}") for seed in seeds]
        res_list = []
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_run_melon_match, t): t for t in tasks}
            for future in as_completed(futures):
                res_list.append(future.result())

        d8 = statistics.mean([r["d8_cash"] for r in res_list])
        d15 = statistics.mean([r["d15_cash"] for r in res_list])
        final = statistics.mean([r["final_cash"] for r in res_list])
        v41_avg = statistics.mean([r["final_v41"] for r in res_list])
        wins = sum(1 for r in res_list if r["win"])
        win_rate = (wins / len(seeds)) * 100.0

        results_by_count[count] = {
            "melon_count": count,
            "win_rate": win_rate,
            "avg_d8": round(d8, 2),
            "avg_d15": round(d15, 2),
            "avg_final": round(final, 2),
            "avg_v41": round(v41_avg, 2),
            "margin": round(final - v41_avg, 2),
        }

    print("\n" + "=" * 95)
    print(" MELON OPENING FINE-TUNING CURVE SUMMARY TABLE (150 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<10} | {'Opening Strategy':<28} | {'Day-8 Cash':<14} | {'Day-15 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)
    for count in [10, 11, 12]:
        r = results_by_count[count]
        print(f"P2-{count:<5} | {count} Opening Melons              | ${r['avg_d8']:<13,.2f} | ${r['avg_d15']:<13,.2f} | ${r['avg_final']:<15,.2f} | {r['win_rate']:.1f}%")
    print("=" * 95)

    best_count = max(results_by_count.values(), key=lambda x: x["avg_final"])["melon_count"]
    print(f"\n OPTIMAL OPENING MELON COUNT DISCOVERED: {best_count} Melons")

    with open("quick_melon_curve_results.json", "w") as f:
        json.dump(results_by_count, f, indent=2)

if __name__ == "__main__":
    main()
