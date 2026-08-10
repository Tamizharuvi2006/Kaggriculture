"""Isolated 3-Variant Ablation Benchmark & Cow 9-13 ROI Analytics.

Evaluates 300 total matches across Seeds 1000-1049 (100 matches per variant vs V4.1 Master Champion):
- V4.1A: V4.1 Core + Remove 8-Cow Cap (Ranker OFF)
- V4.1B: V4.1 Core + Milk Ranker (8-Cow Cap ON)
- V8.4:  V4.1 Core + Remove Cap + Milk Ranker (Combined)

Computes:
1. Win Rate vs V4.1 (%)
2. Average Wealth ($)
3. Worst-case Floor Score ($)
4. ROI of Cows 9-13 = (Extra Milk Revenue) / (Cost of Cows 9-13 + Feed)
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

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_variant(variant_name, process_id):
    spec = importlib.util.spec_from_file_location(f"{variant_name}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if variant_name == "V41":
        # Pure V4.1 Master Champion (8-Cow Cap ON, Ranker OFF)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "cows": 8,
        })
        return mod.agent, mod

    elif variant_name == "V41A":
        # V4.1A: Remove 8-Cow Cap (Cows=13, Ranker OFF)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "cows": 13,
        })
        return mod.agent, mod

    elif variant_name == "V41B":
        # V4.1B: Milk Ranker ON (8-Cow Cap ON)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "cows": 8,
        })
        _base = mod.agent

        def agent_v41b(obs, configuration=None):
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

        return agent_v41b, mod

    elif variant_name == "V84":
        # V84: Remove Cap (Cows=13) + Milk Ranker ON
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "cows": 13,
        })
        _base = mod.agent

        def agent_v84(obs, configuration=None):
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

        return agent_v84, mod


def _run_ablation_match(args):
    variant_name, seed, process_id = args
    try:
        agent_var, _ = _load_variant(variant_name, f"{process_id}_var")
        agent_v41, _ = _load_variant("V41", f"{process_id}_v41")

        # Swap seat positions 50-50
        p0_is_var = (seed % 2 == 0)
        p0_agent = agent_var if p0_is_var else agent_v41
        p1_agent = agent_v41 if p0_is_var else agent_var

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.run([p0_agent, p1_agent])

        s0 = float(env.steps[-1][0]["observation"]["farms"][0]["money"])
        s1 = float(env.steps[-1][1]["observation"]["farms"][1]["money"])

        s_var = s0 if p0_is_var else s1
        s_v41 = s1 if p0_is_var else s0

        return {
            "variant": variant_name,
            "seed": seed,
            "s_var": s_var,
            "s_v41": s_v41,
            "win": s_var > s_v41,
            "error": None,
        }
    except Exception as e:
        return {
            "variant": variant_name,
            "seed": seed,
            "s_var": 0.0,
            "s_v41": 0.0,
            "win": False,
            "error": str(e),
        }


def run_variant_benchmark(variant_name, seeds, max_workers=4):
    print(f"\n--- ABLATION BENCHMARK: {variant_name} vs V41 Master Champion (100 Matches) ---")
    tasks = [(variant_name, seed, f"{variant_name}_{seed}") for seed in seeds]
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_ablation_match, t): t for t in tasks}
        for future in as_completed(futures):
            results.append(future.result())

    var_scores = [r["s_var"] for r in results]
    v41_scores = [r["s_v41"] for r in results]
    wins = sum(1 for r in results if r["win"])

    mean_var = statistics.mean(var_scores)
    mean_v41 = statistics.mean(v41_scores)
    margin = mean_var - mean_v41
    worst_case = min(var_scores)

    print(f"  {variant_name} Win Rate:     {wins}/100 ({(wins/100)*100:.1f}%)")
    print(f"  {variant_name} Avg Score:    ${mean_var:,.2f} vs V41 Avg ${mean_v41:,.2f} (Margin: +${margin:,.2f})")
    print(f"  {variant_name} Worst Floor:  ${worst_case:,.2f}")

    return {
        "variant": variant_name,
        "win_rate": (wins / 100) * 100,
        "mean_score": round(mean_var, 2),
        "mean_v41_score": round(mean_v41, 2),
        "victory_margin": round(margin, 2),
        "worst_floor": round(worst_case, 2),
    }


def main():
    print("=" * 90)
    print(" ISOLATED ABLATION BENCHMARK: V4.1A vs V4.1B vs V8.4 (300 Matches)")
    print("=" * 90)

    # 100 seeds for statistical validity (Seeds 1000-1099)
    seeds = list(range(1000, 1100))

    # Variant V4.1A: Remove Cap (Cows=13, Ranker OFF)
    res_a = run_variant_benchmark("V41A", seeds)

    # Variant V4.1B: Milk Ranker ON (8-Cow Cap ON)
    res_b = run_variant_benchmark("V41B", seeds)

    # Variant V8.4: Remove Cap (Cows=13) + Milk Ranker ON
    res_84 = run_variant_benchmark("V84", seeds)

    # ROI Calculation for Cows 9-13
    # Cost per additional cow = $300 (pasture/cow) + $150 (feed reserve) = $450
    # 5 additional cows (9-13) = $2,250 investment cost
    extra_wealth_uncapped = res_a["mean_score"] - res_a["mean_v41_score"]
    cows_9_13_cost = 2250.0
    cows_9_13_roi = (extra_wealth_uncapped / cows_9_13_cost) * 100.0 if cows_9_13_cost > 0 else 0.0

    print("\n" + "=" * 95)
    print(" ABLATION SUMMARY TABLE & COWS 9-13 ROI ANALYTICS")
    print("=" * 95)
    print(f"{'Variant':<10} | {'Architecture Change':<30} | {'Win Rate':<12} | {'Avg Wealth ($)':<16} | {'Margin ($)':<12} | {'Floor ($)':<12}")
    print("-" * 95)
    print(f"{'V4.1A':<10} | {'Remove 8-Cow Cap (Cows=13)':<30} | {res_a['win_rate']:.1f}%       | ${res_a['mean_score']:<15,.2f} | +${res_a['victory_margin']:<11,.2f} | ${res_a['worst_floor']:<11,.2f}")
    print(f"{'V4.1B':<10} | {'Milk Ranker ON (8-Cow Cap)':<30} | {res_b['win_rate']:.1f}%       | ${res_b['mean_score']:<15,.2f} | +${res_b['victory_margin']:<11,.2f} | ${res_b['worst_floor']:<11,.2f}")
    print(f"{'V8.4':<10} | {'Remove Cap + Milk Ranker':<30} | {res_84['win_rate']:.1f}%       | ${res_84['mean_score']:<15,.2f} | +${res_84['victory_margin']:<11,.2f} | ${res_84['worst_floor']:<11,.2f}")
    print("-" * 95)
    print(f" COWS 9-13 NET ROI: {cows_9_13_roi:.1f}% (Net Extra Wealth: +${extra_wealth_uncapped:,.2f} on $2,250 Investment)")
    print("=" * 95)

    report = {
        "res_v41a": res_a,
        "res_v41b": res_b,
        "res_v84": res_84,
        "cows_9_13_roi_percent": round(cows_9_13_roi, 1),
        "extra_wealth_uncapped": round(extra_wealth_uncapped, 2),
    }
    with open("ablation_v41a_v41b_v84_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
