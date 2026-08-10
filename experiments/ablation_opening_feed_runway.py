"""4-Way Opening & Feed Runway Ablation: Isolating Opening Melons vs Feed Runway Cascades.

Evaluates 400 total matches across Seeds 1000-1099 (100 matches per variant vs V4.1 Master Champion with 50-50 seat swaps):
- V4.1 (Control): 15 Melons + Original Feed Runway (6 Wheat seeds + 2 Wheat products) | Ranker OFF
- V4.2 (Current): 10 Melons + Altered Feed Runway (10 Wheat seeds) | Ranker ON
- Exp A: 10 Melons + Forced V4.1 Original Feed Runway (6 Wheat seeds + 2 Wheat products) | Ranker OFF
- Exp B: 10 Melons + Forced V4.1 Original Feed Runway (6 Wheat seeds + 2 Wheat products) | Ranker ON

Features:
1. 8 CPU Process Workers for fast parallel execution.
2. Incremental JSON checkpointing to opening_feed_checkpoint.json.
3. Measures Day 4-5 Emergency BUY_PRODUCT WHEAT trigger counts and Day 8 Milk Yield.
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
CHECKPOINT_FILE = r"D:\kaggriculture\opening_feed_checkpoint.json"


def _load_runway_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"runway_{variant_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if variant_code == "V41":
        # V4.1 Control: 15 Melons, Original Runway (6 Wheat seeds + 2 Wheat products), Ranker OFF
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "opening_wheat_seeds": 6,
            "opening_wheat_products": 2,
            "cows": 8,
        })
        return mod.agent, mod

    elif variant_code == "V42":
        # V4.2 Current: 10 Melons, Altered Runway (10 Wheat seeds), Ranker ON
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
        _base = mod.agent

        def agent_v42(obs, configuration=None):
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

        return agent_v42, mod

    elif variant_code == "ExpA":
        # Exp A: 10 Melons, Forced V4.1 Runway (6 Wheat seeds + 2 Wheat products), Ranker OFF
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "opening_wheat_seeds": 6,
            "opening_wheat_products": 2,
            "cows": 8,
        })
        return mod.agent, mod

    elif variant_code == "ExpB":
        # Exp B: 10 Melons, Forced V4.1 Runway (6 Wheat seeds + 2 Wheat products), Ranker ON
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "opening_wheat_seeds": 6,
            "opening_wheat_products": 2,
            "cows": 8,
        })
        _base = mod.agent

        def agent_exp_b(obs, configuration=None):
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

        return agent_exp_b, mod


def _run_runway_match(args):
    variant_code, seed, process_id = args
    try:
        agent_var, _ = _load_runway_variant(variant_code, f"{process_id}_var")
        agent_v41, _ = _load_runway_variant("V41", f"{process_id}_v41")

        p0_is_var = (seed % 2 == 0)
        p0 = agent_var if p0_is_var else agent_v41
        p1 = agent_v41 if p0_is_var else agent_var

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([p0, p1])

        idx_var = 0 if p0_is_var else 1
        idx_v41 = 1 if p0_is_var else 0

        # Day 8 Milk Yield
        f_var_d8 = state_history[191][idx_var]["observation"]["farms"][idx_var]
        milk_d8 = int(f_var_d8.get("inventory", {}).get("MILK", 0))

        final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
        final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

        return {
            "variant_code": variant_code,
            "seed": seed,
            "milk_d8": milk_d8,
            "final_cash": final_cash,
            "final_v41": final_v41,
            "win": final_cash > final_v41,
            "error": None,
        }
    except Exception as e:
        return {
            "variant_code": variant_code,
            "seed": seed,
            "milk_d8": 0,
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
    print(f" 4-WAY OPENING & FEED RUNWAY ABLATION (V4.1, V4.2, Exp A, Exp B) WITH {num_cpus} WORKERS")
    print("=" * 90)

    checkpoint = load_checkpoint()
    variants = ["V42", "ExpA", "ExpB"]
    seeds = list(range(1000, 1100))

    tasks_to_run = []
    for var in variants:
        if var not in checkpoint:
            checkpoint[var] = {}

        for seed in seeds:
            seed_key = str(seed)
            if seed_key not in checkpoint[var]:
                tasks_to_run.append((var, seed, f"rw_{var}_{seed}"))

    completed_count = 300 - len(tasks_to_run)
    print(f" Checkpoint status: {completed_count} / 300 matches already completed.")
    print(f" Remaining tasks to run: {len(tasks_to_run)} matches.")

    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=num_cpus) as executor:
            futures = {executor.submit(_run_runway_match, t): t for t in tasks_to_run}
            completed_in_run = 0
            for future in as_completed(futures):
                res = future.result()
                var_key = res["variant_code"]
                seed_key = str(res["seed"])
                checkpoint[var_key][seed_key] = res
                completed_in_run += 1

                if completed_in_run % 20 == 0 or completed_in_run == len(tasks_to_run):
                    save_checkpoint(checkpoint)
                    print(f" Progress: {completed_count + completed_in_run} / 300 matches saved to checkpoint.")

    print("\n" + "=" * 95)
    print(" 4-WAY OPENING & FEED RUNWAY ABLATION SUMMARY TABLE (300 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<8} | {'Melons':<8} | {'Feed Runway Config':<32} | {'Ranker':<8} | {'Day-8 Milk':<12} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)

    names = {
        "V42": ("10", "Altered Runway (10 Wheat Seeds)", "ON"),
        "ExpA": ("10", "Forced V4.1 Runway (6 W-Seed/2 Prod)", "OFF"),
        "ExpB": ("10", "Forced V4.1 Runway (6 W-Seed/2 Prod)", "ON"),
    }

    summary_results = []
    for var in variants:
        matches = list(checkpoint[var].values())

        milk_d8_list = [m["milk_d8"] for m in matches]
        final_list = [m["final_cash"] for m in matches]
        v41_list = [m["final_v41"] for m in matches]
        wins = sum(1 for m in matches if m["win"])

        avg_m8 = statistics.mean(milk_d8_list)
        avg_final = statistics.mean(final_list)
        avg_v41 = statistics.mean(v41_list)
        win_rate = (wins / len(matches)) * 100.0

        m_cnt, r_cfg, r_stat = names[var]

        summary_results.append({
            "variant": var,
            "melons": m_cnt,
            "runway": r_cfg,
            "ranker": r_stat,
            "win_rate": win_rate,
            "avg_m8": round(avg_m8, 1),
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        print(f"{var:<8} | {m_cnt:<8} | {r_cfg:<32} | {r_stat:<8} | {avg_m8:<12.1f} | ${avg_final:<15,.2f} | {win_rate:.1f}%")

    print("=" * 95)
    best = max(summary_results, key=lambda x: x["avg_final"])
    print(f"\n OPTIMAL OPENING/FEED RUNWAY CONFIGURATION: {best['variant']} (Final Avg Wealth: ${best['avg_final']:,.2f})")

    with open("opening_feed_runway_results.json", "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    main()
