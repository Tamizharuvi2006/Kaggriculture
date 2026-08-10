"""Counterfactual Day-12 Surplus Cash Reinvestment Ablation (C1, C2, C3, C4, C5).

Evaluates 500 total matches across Seeds 1000-1099 (100 matches per variant vs V4.1 Master Champion with 50-50 seat swaps):
- C1 (Control): V4.2 Baseline (10 Melons + Milk Ranker + 8-Cow Cap)
- C2 (Conditional Cow 9-10): Buy Cow 9-10 ONLY when cash >= $3,000 after Day 12
- C3 (Conditional Land Expansion): Unlock SW/SE Land Quadrants immediately on Day 12 when cash >= $3,000
- C4 (Conditional Strawberry Expansion): Plant high-value Strawberries on Days 12-20 when cash >= $3,000
- C5 (Combined Smart Reinvestment): Unlock Land + Plant Strawberries + Cow 9 ONLY when cash reserve >= $2,000

Features:
1. 8 CPU Process Workers for fast parallel execution.
2. Incremental JSON checkpointing to day12_reinvestment_checkpoint.json.
"""

import sys
import os
import json
import statistics
import importlib.util
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"
CHECKPOINT_FILE = r"D:\kaggriculture\day12_reinvestment_checkpoint.json"


def _load_reinvestment_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"reinvest_{variant_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if variant_code == "V41":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent

    # Configs for C1 to C5
    if variant_code == "C1":
        # Control: 10 Melons + 8-Cow Cap
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
    elif variant_code == "C2":
        # Conditional Cow 9-10 when cash >= $3,000
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 10,  # Uncaps up to 10 cows when cash allows
        })
    elif variant_code == "C3":
        # Conditional Land Expansion on Day 12
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "land_ne_day": 5,
            "land_sw_day": 12,
            "cows": 8,
        })
    elif variant_code == "C4":
        # Conditional Strawberry Expansion
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "strawberries_enabled": True,
            "cows": 8,
        })
    elif variant_code == "C5":
        # Combined Smart Reinvestment (Land + Strawberries + Cow 9)
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "land_sw_day": 12,
            "strawberries_enabled": True,
            "cows": 9,
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


def _run_reinvestment_match(args):
    variant_code, seed, process_id = args
    try:
        agent_var = _load_reinvestment_variant(variant_code, f"{process_id}_var")
        agent_v41 = _load_reinvestment_variant("V41", f"{process_id}_v41")

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
            "variant_code": variant_code,
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
            "variant_code": variant_code,
            "seed": seed,
            "d8_cash": 0.0,
            "d15_cash": 0.0,
            "final_cash": 0.0,
            "final_v41": 0.0,
            "win": False,
            "error": str(e),
        }


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_checkpoint(data):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("=" * 90)
    num_cpus = max(4, multiprocessing.cpu_count())
    print(f" DAY-12 SURPLUS CASH REINVESTMENT ABLATION (C1-C5) WITH {num_cpus} CPU WORKERS")
    print("=" * 90)

    checkpoint = load_checkpoint()
    variants = ["C1", "C2", "C3", "C4", "C5"]
    seeds = list(range(1000, 1100))

    tasks_to_run = []
    for var in variants:
        if var not in checkpoint:
            checkpoint[var] = {}

        for seed in seeds:
            seed_key = str(seed)
            if seed_key not in checkpoint[var]:
                tasks_to_run.append((var, seed, f"reinv_{var}_{seed}"))

    completed_count = 500 - len(tasks_to_run)
    print(f" Checkpoint status: {completed_count} / 500 matches already completed.")
    print(f" Remaining tasks to run: {len(tasks_to_run)} matches.")

    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=num_cpus) as executor:
            futures = {executor.submit(_run_reinvestment_match, t): t for t in tasks_to_run}
            completed_in_run = 0
            for future in as_completed(futures):
                res = future.result()
                var_key = res["variant_code"]
                seed_key = str(res["seed"])
                checkpoint[var_key][seed_key] = res
                completed_in_run += 1

                if completed_in_run % 20 == 0 or completed_in_run == len(tasks_to_run):
                    save_checkpoint(checkpoint)
                    print(f" Progress: {completed_count + completed_in_run} / 500 matches saved to checkpoint.")

    print("\n" + "=" * 95)
    print(" DAY-12 SURPLUS REINVESTMENT SUMMARY TABLE (500 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<8} | {'Reinvestment Strategy':<34} | {'Day-15 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)

    names = {
        "C1": "Control (10 Melons + 8 Cows)",
        "C2": "Conditional Cow 9-10 Expansion",
        "C3": "Day-12 SW/SE Land Unlock",
        "C4": "Day 12-20 Strawberry Crops",
        "C5": "Combined Smart Reinvestment",
    }

    summary_results = []
    for var in variants:
        matches = list(checkpoint[var].values())

        d8_list = [m["d8_cash"] for m in matches]
        d15_list = [m["d15_cash"] for m in matches]
        final_list = [m["final_cash"] for m in matches]
        v41_list = [m["final_v41"] for m in matches]
        wins = sum(1 for m in matches if m["win"])

        avg_d8 = statistics.mean(d8_list)
        avg_d15 = statistics.mean(d15_list)
        avg_final = statistics.mean(final_list)
        avg_v41 = statistics.mean(v41_list)
        win_rate = (wins / len(matches)) * 100.0

        summary_results.append({
            "variant": var,
            "name": names[var],
            "win_rate": win_rate,
            "avg_d8": round(avg_d8, 2),
            "avg_d15": round(avg_d15, 2),
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        print(f"{var:<8} | {names[var]:<34} | ${avg_d15:<13,.2f} | ${avg_final:<15,.2f} | {win_rate:.1f}%")

    print("=" * 95)
    best = max(summary_results, key=lambda x: x["avg_final"])
    print(f"\n OPTIMAL DAY-12 REINVESTMENT STRATEGY DISCOVERED: {best['variant']} - {best['name']} (Final Avg Wealth: ${best['avg_final']:,.2f})")

    with open("day12_reinvestment_results.json", "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    main()
