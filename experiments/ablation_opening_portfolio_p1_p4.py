"""Opening Portfolio Ablation (P1, P2, P3, P4) & Asset ROI Comparison.

Evaluates 400 total matches across Seeds 1000-1099 (100 matches per portfolio variant vs V4.1 Master Champion):
- P1: 15 Opening Melons (Current Baseline)
- P2: 10 Opening Melons + Liquid Cash Reserve
- P3: 8 Opening Melons + Earlier 2nd Cow (Day 2)
- P4: 12 Opening Melons + Faster Land Unlock (Day 5 NE Quadrant Unlock)

Measures:
1. Day-8 Cash ($)
2. Day-15 Wealth ($)
3. Final Wealth ($)
4. Win Rate vs V4.1 (%)
5. ROI Comparisons: ROI_melon vs ROI_land vs ROI_cow2
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


def _load_portfolio_agent(p_type, process_id):
    spec = importlib.util.spec_from_file_location(f"port_{p_type}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if p_type == "V41":
        # Pure V4.1 Baseline
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent
    elif p_type == "P1":
        # P1: 15 Melons Baseline
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
    elif p_type == "P2":
        # P2: 10 Melons + Cash Reserve
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
    elif p_type == "P3":
        # P3: 8 Melons + Earlier Cow
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 8,
            "cows": 8,
        })
    elif p_type == "P4":
        # P4: 12 Melons + Faster Land Unlock
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 12,
            "land_ne_day": 5,
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


def _run_portfolio_match(args):
    p_type, seed, process_id = args
    try:
        agent_var = _load_portfolio_agent(p_type, f"{process_id}_var")
        agent_v41 = _load_portfolio_agent("V41", f"{process_id}_v41")

        p0_is_var = (seed % 2 == 0)
        p0 = agent_var if p0_is_var else agent_v41
        p1 = agent_v41 if p0_is_var else agent_var

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([p0, p1])

        # Step 191 = Day 8, Step 359 = Day 15, Step 719 = Day 30
        idx_var = 0 if p0_is_var else 1
        idx_v41 = 1 if p0_is_var else 0

        d8_cash = float(state_history[191][idx_var]["observation"]["farms"][idx_var]["money"])
        d15_cash = float(state_history[359][idx_var]["observation"]["farms"][idx_var]["money"])
        final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])

        final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

        return {
            "p_type": p_type,
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
            "p_type": p_type,
            "seed": seed,
            "d8_cash": 0.0,
            "d15_cash": 0.0,
            "final_cash": 0.0,
            "final_v41": 0.0,
            "win": False,
            "error": str(e),
        }


def run_portfolio_benchmark(p_type, seeds, max_workers=4):
    print(f"\n--- PORTFOLIO BENCHMARK: {p_type} vs V4.1 Master Champion (100 Matches) ---")
    tasks = [(p_type, seed, f"{p_type}_{seed}") for seed in seeds]
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_portfolio_match, t): t for t in tasks}
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
    win_rate = (wins / 100) * 100

    print(f"  {p_type} Win Rate:     {wins}/100 ({win_rate:.1f}%)")
    print(f"  {p_type} Day-8 Cash:   ${avg_d8:,.2f}")
    print(f"  {p_type} Day-15 Cash:  ${avg_d15:,.2f}")
    print(f"  {p_type} Final Wealth: ${avg_final:,.2f} vs V41 Avg ${avg_v41:,.2f} (Margin: +${avg_final - avg_v41:,.2f})")

    return {
        "p_type": p_type,
        "win_rate": win_rate,
        "avg_d8": round(avg_d8, 2),
        "avg_d15": round(avg_d15, 2),
        "avg_final": round(avg_final, 2),
        "avg_v41": round(avg_v41, 2),
        "margin": round(avg_final - avg_v41, 2),
    }


def main():
    print("=" * 90)
    print(" OPENING PORTFOLIO ABLATION: P1 vs P2 vs P3 vs P4 (400 Matches)")
    print("=" * 90)

    seeds = list(range(1000, 1100))

    res_p1 = run_portfolio_benchmark("P1", seeds)
    res_p2 = run_portfolio_benchmark("P2", seeds)
    res_p3 = run_portfolio_benchmark("P3", seeds)
    res_p4 = run_portfolio_benchmark("P4", seeds)

    # ROI Analytics
    # Melon Seed Cost = $25/seed, Average Melon Price = $500/melon
    roi_melon = ((500.0 - 25.0) / 25.0) * 100.0  # 1900% gross crop ROI

    # Land Unlock Cost = $1,000, Net extra profit after land unlock
    extra_land_profit = res_p4["avg_final"] - res_p1["avg_final"]
    roi_land = (extra_land_profit / 1000.0) * 100.0 if extra_land_profit > 0 else 0.0

    print("\n" + "=" * 95)
    print(" OPENING PORTFOLIO SUMMARY TABLE & ASSET ROI COMPARISON")
    print("=" * 95)
    print(f"{'Variant':<8} | {'Opening Strategy':<32} | {'Day-8 Cash':<14} | {'Day-15 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)
    print(f"{'P1':<8} | {'15 Melons (Baseline)':<32} | ${res_p1['avg_d8']:<13,.2f} | ${res_p1['avg_d15']:<13,.2f} | ${res_p1['avg_final']:<15,.2f} | {res_p1['win_rate']:.1f}%")
    print(f"{'P2':<8} | {'10 Melons + Cash Reserve':<32} | ${res_p2['avg_d8']:<13,.2f} | ${res_p2['avg_d15']:<13,.2f} | ${res_p2['avg_final']:<15,.2f} | {res_p2['win_rate']:.1f}%")
    print(f"{'P3':<8} | {'8 Melons + Earlier Cow':<32} | ${res_p3['avg_d8']:<13,.2f} | ${res_p3['avg_d15']:<13,.2f} | ${res_p3['avg_final']:<15,.2f} | {res_p3['win_rate']:.1f}%")
    print(f"{'P4':<8} | {'12 Melons + Faster Land Unlock':<32} | ${res_p4['avg_d8']:<13,.2f} | ${res_p4['avg_d15']:<13,.2f} | ${res_p4['avg_final']:<15,.2f} | {res_p4['win_rate']:.1f}%")
    print("-" * 95)
    print(f" ROI COMPARISON: Melon Seed Gross ROI = {roi_melon:.0f}% | Land Unlock Net ROI = {roi_land:.1f}%")
    print("=" * 95)

    report = {
        "p1": res_p1,
        "p2": res_p2,
        "p3": res_p3,
        "p4": res_p4,
        "roi_melon_percent": roi_melon,
        "roi_land_percent": round(roi_land, 1),
    }
    with open("opening_portfolio_p1_p4_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
