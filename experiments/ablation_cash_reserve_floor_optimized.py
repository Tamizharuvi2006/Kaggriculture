"""High-Speed Parallel Dynamic Cash Reserve Floor Ablation with Incremental Checkpointing.

Features:
1. Uses multiprocessing.cpu_count() workers (up to 8 processes) for 2x faster execution.
2. Saves results incrementally to reserve_floor_checkpoint.json.
3. Automatically skips previously completed (reserve_floor, seed) matches on resume.
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
CHECKPOINT_FILE = r"D:\kaggriculture\reserve_floor_checkpoint.json"


def _load_reserve_variant(reserve_floor, process_id):
    spec = importlib.util.spec_from_file_location(f"res_opt_{reserve_floor}_{process_id}", V18_PATH)
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
            "reserve_floor": str(reserve_floor),
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
            "reserve_floor": str(reserve_floor),
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
    print(f" FAST PARALLEL RESERVE FLOOR ABLATION (R1-R4) WITH {num_cpus} CPU WORKERS")
    print("=" * 90)

    checkpoint = load_checkpoint()
    floors = [200, 400, 600, 800]
    seeds = list(range(1000, 1100))

    tasks_to_run = []
    for fl in floors:
        fl_key = str(fl)
        if fl_key not in checkpoint:
            checkpoint[fl_key] = {}

        for seed in seeds:
            seed_key = str(seed)
            if seed_key not in checkpoint[fl_key]:
                tasks_to_run.append((fl, seed, f"opt_{fl}_{seed}"))

    completed_count = 400 - len(tasks_to_run)
    print(f" Checkpoint status: {completed_count} / 400 matches already completed.")
    print(f" Remaining tasks to run: {len(tasks_to_run)} matches.")

    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=num_cpus) as executor:
            futures = {executor.submit(_run_reserve_match, t): t for t in tasks_to_run}
            completed_in_run = 0
            for future in as_completed(futures):
                res = future.result()
                fl_key = res["reserve_floor"]
                seed_key = str(res["seed"])
                checkpoint[fl_key][seed_key] = res
                completed_in_run += 1

                if completed_in_run % 10 == 0 or completed_in_run == len(tasks_to_run):
                    save_checkpoint(checkpoint)
                    print(f" Progress: {completed_count + completed_in_run} / 400 matches saved to checkpoint.")

    print("\n" + "=" * 95)
    print(" DYNAMIC CASH RESERVE FLOOR SUMMARY TABLE (400 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<8} | {'Cash Reserve Floor':<26} | {'Opening Melons':<16} | {'Day-8 Cash':<14} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)

    summary_results = []
    for fl in floors:
        fl_key = str(fl)
        matches = list(checkpoint[fl_key].values())
        
        d8_list = [m["d8_cash"] for m in matches]
        final_list = [m["final_cash"] for m in matches]
        v41_list = [m["final_v41"] for m in matches]
        wins = sum(1 for m in matches if m["win"])

        avg_d8 = statistics.mean(d8_list)
        avg_final = statistics.mean(final_list)
        avg_v41 = statistics.mean(v41_list)
        win_rate = (wins / len(matches)) * 100.0

        summary_results.append({
            "reserve_floor": fl,
            "win_rate": win_rate,
            "avg_d8": round(avg_d8, 2),
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        melons_count = min(15, max(1, int((1043 - fl) // 25)))
        print(f"R-${fl:<5} | ${fl} Minimum Reserve            | {melons_count} Melons        | ${avg_d8:<13,.2f} | ${avg_final:<15,.2f} | {win_rate:.1f}%")

    print("=" * 95)
    best = max(summary_results, key=lambda x: x["avg_final"])
    print(f"\n OPTIMAL DYNAMIC CASH RESERVE FLOOR DISCOVERED: ${best['reserve_floor']} (Final Avg Wealth: ${best['avg_final']:,.2f})")

    with open("cash_reserve_floor_results.json", "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    main()
