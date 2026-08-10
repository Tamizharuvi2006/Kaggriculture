"""Authoritative Master Baseline Reconciliation Benchmark.

Evaluates all 4 core configurations across the EXACT SAME 100 seeds (1000 to 1099)
with 50-50 seat-swapped 1v1 competition against V4.1 Master Champion:

1. Config 1: V4.1 Ground Truth Master (15 Melons, Ranker OFF, 8 Cows) - Baseline Control
2. Config 2: V4.1 + 10-Melon Opening Only (10 Melons, Ranker OFF, 8 Cows)
3. Config 3: V4.1 + Milk Ranker Only (15 Melons, Ranker ON, 8 Cows)
4. Config 4: V4.2 Combined Candidate (10 Melons, Ranker ON, 8 Cows)

Features:
1. 8 CPU Process Workers for fast parallel execution.
2. Incremental JSON checkpointing to master_baseline_checkpoint.json.
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
CHECKPOINT_FILE = r"D:\kaggriculture\master_baseline_checkpoint.json"


def _load_config_agent(config_code, process_id):
    spec = importlib.util.spec_from_file_location(f"mb_{config_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if config_code == "Config1":
        # V4.1 Baseline Control: 15 Melons, Ranker OFF
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent

    elif config_code == "Config2":
        # 10-Melon Opening Only: 10 Melons, Ranker OFF
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
        return mod.agent

    elif config_code == "Config3":
        # Milk Ranker Only: 15 Melons, Ranker ON
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        _base = mod.agent

        def agent_cfg3(obs, configuration=None):
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

        return agent_cfg3

    elif config_code == "Config4":
        # V4.2 Combined Candidate: 10 Melons, Ranker ON
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
        _base = mod.agent

        def agent_cfg4(obs, configuration=None):
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

        return agent_cfg4


def _run_mb_match(args):
    config_code, seed, process_id = args
    try:
        agent_cfg = _load_config_agent(config_code, f"{process_id}_cfg")
        agent_v41 = _load_config_agent("Config1", f"{process_id}_v41")

        p0_is_cfg = (seed % 2 == 0)
        p0 = agent_cfg if p0_is_cfg else agent_v41
        p1 = agent_v41 if p0_is_cfg else agent_cfg

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([p0, p1])

        idx_cfg = 0 if p0_is_cfg else 1
        idx_v41 = 1 if p0_is_cfg else 0

        final_cash = float(state_history[-1][idx_cfg]["observation"]["farms"][idx_cfg]["money"])
        final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

        return {
            "config_code": config_code,
            "seed": seed,
            "final_cash": final_cash,
            "final_v41": final_v41,
            "win": final_cash > final_v41,
            "error": None,
        }
    except Exception as e:
        return {
            "config_code": config_code,
            "seed": seed,
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
    print(f" AUTHORITATIVE MASTER BASELINE RECONCILIATION BENCHMARK ({num_cpus} CPU WORKERS)")
    print("=" * 90)

    checkpoint = load_checkpoint()
    configs = ["Config1", "Config2", "Config3", "Config4"]
    seeds = list(range(1000, 1100))

    tasks_to_run = []
    for cfg in configs:
        if cfg not in checkpoint:
            checkpoint[cfg] = {}

        for seed in seeds:
            seed_key = str(seed)
            if seed_key not in checkpoint[cfg]:
                tasks_to_run.append((cfg, seed, f"mb_{cfg}_{seed}"))

    completed_count = 400 - len(tasks_to_run)
    print(f" Checkpoint status: {completed_count} / 400 matches already completed.")
    print(f" Remaining tasks to run: {len(tasks_to_run)} matches.")

    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=num_cpus) as executor:
            futures = {executor.submit(_run_mb_match, t): t for t in tasks_to_run}
            completed_in_run = 0
            for future in as_completed(futures):
                res = future.result()
                cfg_key = res["config_code"]
                seed_key = str(res["seed"])
                checkpoint[cfg_key][seed_key] = res
                completed_in_run += 1

                if completed_in_run % 20 == 0 or completed_in_run == len(tasks_to_run):
                    save_checkpoint(checkpoint)
                    print(f" Progress: {completed_count + completed_in_run} / 400 matches saved to checkpoint.")

    print("\n" + "=" * 95)
    print(" AUTHORITATIVE MASTER BASELINE MATRIX (400 MATCHES, SEEDS 1000-1099)")
    print("=" * 95)
    print(f"{'Config':<10} | {'Strategy Architecture':<34} | {'Final Cash ($)':<16} | {'Win Rate vs V4.1':<18} | {'Worst Floor ($)':<16}")
    print("-" * 95)

    names = {
        "Config1": "V4.1 Ground Truth (15 Melons, Ranker OFF)",
        "Config2": "V4.1 + 10-Melon Opening Only",
        "Config3": "V4.1 + Milk Ranker Only",
        "Config4": "V4.2 Combined (10 Melons + Milk Ranker)",
    }

    summary_results = []
    for cfg in configs:
        matches = list(checkpoint[cfg].values())

        final_list = [m["final_cash"] for m in matches]
        v41_list = [m["final_v41"] for m in matches]
        wins = sum(1 for m in matches if m["win"])

        avg_final = statistics.mean(final_list)
        avg_v41 = statistics.mean(v41_list)
        win_rate = (wins / len(matches)) * 100.0

        summary_results.append({
            "config": cfg,
            "name": names[cfg],
            "win_rate": win_rate,
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
            "worst_case": round(min(final_list), 2),
        })

        print(f"{cfg:<10} | {names[cfg]:<34} | ${avg_final:<15,.2f} | {win_rate:<17.1f}% | ${min(final_list):<15,.2f}")

    print("=" * 95)

    with open("authoritative_master_baseline_results.json", "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    main()
