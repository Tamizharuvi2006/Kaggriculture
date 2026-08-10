"""Dynamic Cash Reserve Floor Ablation: R1 ($200) vs R2 ($400) vs R3 ($600) vs R4 ($800).

Evaluates 400 total matches across Seeds 1000-1099 (100 matches per reserve rule vs V4.1 Master Champion):
- R1: Minimum Cash Floor = $200 before Day 8
- R2: Minimum Cash Floor = $400 before Day 8
- R3: Minimum Cash Floor = $600 before Day 8 (User Hypothesis)
- R4: Minimum Cash Floor = $800 before Day 8

Measures:
1. Opening Melon Count Purchased
2. Day-8 Liquid Cash ($)
3. Day-15 Wealth ($)
4. Final Wealth ($)
5. Win Rate vs V4.1 Master Champion (%)
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


def _load_reserve_variant(reserve_floor, process_id):
    spec = importlib.util.spec_from_file_location(f"reserve_{reserve_floor}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if reserve_floor == "V41":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent

    floor_val = float(reserve_floor)
    
    # Calculate max opening melons allowed while keeping cash >= floor_val
    # Starting money = $1,043. Melon seed cost = $25. Max land tiles = 15.
    # Max Melons = min(15, floor((1043 - floor_val) / 25))
    max_melons = min(15, max(1, int((1043.0 - floor_val) // 25.0)))

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": max_melons,
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


def _run_reserve_match(args):
    reserve_floor, seed, process_id = args
    try:
        agent_var = _load_reserve_variant(reserve_floor, f"{process_id}_var")
        agent_v41 = _load_reserve_variant("V41", f"{process_id}_v41")

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
            "reserve_floor": reserve_floor,
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
            "reserve_floor": reserve_floor,
            "seed": seed,
            "d8_cash": 0.0,
            "d15_cash": 0.0,
            "final_cash": 0.0,
            "final_v41": 0.0,
            "win": False,
            "error": str(e),
        }


def run_reserve_benchmark(reserve_floor, seeds, max_workers=4):
    print(f"\n--- DYNAMIC RESERVE BENCHMARK: R (${reserve_floor}) Floor vs V4.1 (100 Matches) ---")
    tasks = [(reserve_floor, seed, f"r_{reserve_floor}_{seed}") for seed in seeds]
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_reserve_match, t): t for t in tasks}
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
    win_rate = (wins / len(seeds)) * 100.0

    print(f"  R (${reserve_floor}) Floor Win Rate:     {wins}/{len(seeds)} ({win_rate:.1f}%)")
    print(f"  R (${reserve_floor}) Floor Day-8 Cash:   ${avg_d8:,.2f}")
    print(f"  R (${reserve_floor}) Floor Day-15 Cash:  ${avg_d15:,.2f}")
    print(f"  R (${reserve_floor}) Floor Final Wealth: ${avg_final:,.2f} vs V41 ${avg_v41:,.2f} (Margin: +${avg_final - avg_v41:,.2f})")

    return {
        "reserve_floor": reserve_floor,
        "win_rate": win_rate,
        "avg_d8": round(avg_d8, 2),
        "avg_d15": round(avg_d15, 2),
        "avg_final": round(avg_final, 2),
        "avg_v41": round(avg_v41, 2),
        "margin": round(avg_final - avg_v41, 2),
    }


def main():
    print("=" * 90)
    print(" DYNAMIC CASH RESERVE FLOOR ABLATION: R1 ($200) vs R2 ($400) vs R3 ($600) vs R4 ($800)")
    print("=" * 90)

    seeds = list(range(1000, 1100))

    res_200 = run_reserve_benchmark(200, seeds)
    res_400 = run_reserve_benchmark(400, seeds)
    res_600 = run_reserve_benchmark(600, seeds)
    res_800 = run_reserve_benchmark(800, seeds)

    print("\n" + "=" * 95)
    print(" DYNAMIC CASH RESERVE FLOOR SUMMARY TABLE (400 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<8} | {'Cash Reserve Floor':<26} | {'Opening Melons':<16} | {'Day-8 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)
    print(f"{'R1':<8} | {'$200 Minimum Reserve':<26} | {int((1043-200)//25)} Melons        | ${res_200['avg_d8']:<13,.2f} | ${res_200['avg_final']:<15,.2f} | {res_200['win_rate']:.1f}%")
    print(f"{'R2':<8} | {'$400 Minimum Reserve':<26} | {int((1043-400)//25)} Melons        | ${res_400['avg_d8']:<13,.2f} | ${res_400['avg_final']:<15,.2f} | {res_400['win_rate']:.1f}%")
    print(f"{'R3':<8} | {'$600 Minimum Reserve':<26} | {int((1043-600)//25)} Melons        | ${res_600['avg_d8']:<13,.2f} | ${res_600['avg_final']:<15,.2f} | {res_600['win_rate']:.1f}%")
    print(f"{'R4':<8} | {'$800 Minimum Reserve':<26} | {int((1043-800)//25)} Melons        | ${res_800['avg_d8']:<13,.2f} | ${res_800['avg_final']:<15,.2f} | {res_800['win_rate']:.1f}%")
    print("=" * 95)

    best_floor = max([res_200, res_400, res_600, res_800], key=lambda x: x["avg_final"])["reserve_floor"]
    print(f"\n OPTIMAL DYNAMIC CASH RESERVE FLOOR DISCOVERED: ${best_floor}")

    report = {
        "res_200": res_200,
        "res_400": res_400,
        "res_600": res_600,
        "res_800": res_800,
        "optimal_reserve_floor": best_floor,
    }
    with open("cash_reserve_floor_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
