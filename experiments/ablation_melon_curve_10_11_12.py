"""Melon Opening Fine-Tuning Ablation: P2A (10 Melons) vs P2B (11 Melons) vs P2C (12 Melons).

Evaluates 600 total matches across Seeds 1000-1199 (200 matches per opening variant vs V4.1 Master Champion):
- P2A: 10 Opening Melons + Cash Reserve
- P2B: 11 Opening Melons + Cash Reserve
- P2C: 12 Opening Melons + Cash Reserve

Measures:
1. Day-8 Cash ($)
2. Day-15 Wealth ($)
3. Final Wealth ($)
4. Win Rate vs V4.1 (%)
5. Identifies the exact global peak of the melon opening curve!
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
    spec = importlib.util.spec_from_file_location(f"melon_{melon_count}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if melon_count == "V41":
        # Pure V4.1 Baseline
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


def run_melon_benchmark(melon_count, seeds, max_workers=4):
    print(f"\n--- MELON CURVE BENCHMARK: {melon_count} Melons vs V4.1 (200 Matches) ---")
    tasks = [(melon_count, seed, f"m_{melon_count}_{seed}") for seed in seeds]
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_melon_match, t): t for t in tasks}
        for future in as_completed(futures):
            results.append(future.result())

    d8_list = [r["d8_cash"] for r in results]
    d15_list = [r["d15_cash"] for r in results]
    final_list = [r["final_cash"] for r in results]
    v41_list = [r["final_v41"] for r in results]
    wins = sum(1 for r in results if r["win"])

    avg_d8 = statistics.mean(d8_list)
    avg_d15 = statistics.mean(d15_list)
    avg_final = statistics.mean(final_list)
    avg_v41 = statistics.mean(v41_list)
    win_rate = (wins / len(seeds)) * 100

    print(f"  {melon_count} Melons Win Rate:     {wins}/{len(seeds)} ({win_rate:.1f}%)")
    print(f"  {melon_count} Melons Day-8 Cash:   ${avg_d8:,.2f}")
    print(f"  {melon_count} Melons Day-15 Cash:  ${avg_d15:,.2f}")
    print(f"  {melon_count} Melons Final Wealth: ${avg_final:,.2f} vs V41 ${avg_v41:,.2f} (Margin: +${avg_final - avg_v41:,.2f})")

    return {
        "melon_count": melon_count,
        "win_rate": win_rate,
        "avg_d8": round(avg_d8, 2),
        "avg_d15": round(avg_d15, 2),
        "avg_final": round(avg_final, 2),
        "avg_v41": round(avg_v41, 2),
        "margin": round(avg_final - avg_v41, 2),
    }


def main():
    print("=" * 90)
    print(" MELON OPENING FINE-TUNING CURVE: 10 vs 11 vs 12 MELONS (600 Matches)")
    print("=" * 90)

    # 200 seeds for high statistical precision (Seeds 1000-1199)
    seeds = list(range(1000, 1200))

    res_10 = run_melon_benchmark(10, seeds)
    res_11 = run_melon_benchmark(11, seeds)
    res_12 = run_melon_benchmark(12, seeds)

    print("\n" + "=" * 95)
    print(" 📊 MELON OPENING FINE-TUNING CURVE SUMMARY TABLE (600 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<10} | {'Opening Strategy':<28} | {'Day-8 Cash':<14} | {'Day-15 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)
    print(f"{'P2A':<10} | {'10 Opening Melons':<28} | ${res_10['avg_d8']:<13,.2f} | ${res_10['avg_d15']:<13,.2f} | ${res_10['avg_final']:<15,.2f} | {res_10['win_rate']:.1f}%")
    print(f"{'P2B':<10} | {'11 Opening Melons':<28} | ${res_11['avg_d8']:<13,.2f} | ${res_11['avg_d15']:<13,.2f} | ${res_11['avg_final']:<15,.2f} | {res_11['win_rate']:.1f}%")
    print(f"{'P2C':<10} | {'12 Opening Melons':<28} | ${res_12['avg_d8']:<13,.2f} | ${res_12['avg_d15']:<13,.2f} | ${res_12['avg_final']:<15,.2f} | {res_12['win_rate']:.1f}%")
    print("=" * 95)

    best_count = max([res_10, res_11, res_12], key=lambda x: x["avg_final"])["melon_count"]
    print(f"\n 💡 OPTIMAL OPENING MELON COUNT DISCOVERED: {best_count} Melons")

    report = {
        "res_10_melons": res_10,
        "res_11_melons": res_11,
        "res_12_melons": res_12,
        "optimal_melon_count": best_count,
    }
    with open("melon_curve_10_11_12_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
