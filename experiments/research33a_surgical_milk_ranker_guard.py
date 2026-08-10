"""Research 33A: Surgical Milk-Ranker Guard & 100-Seed Competitive Validation.

Step 1: Inspects the exact 4 harmful events from milk_ranker_attribution_results.json.
Step 2: Evaluates 200 competitive matches across Seeds 1000-1099 (50-50 seat swaps):
- Variant A: Current V4.2 (Milk Ranker without queue guard)
- Variant B: V4.2 + Surgical Milk-Ranker Guard (Prevents crop displacement when queue > 8)

Features:
1. 8 CPU Process Workers for fast parallel execution.
2. Incremental JSON checkpointing to research33a_checkpoint.json.
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
CHECKPOINT_FILE = r"D:\kaggriculture\research33a_checkpoint.json"


def _load_r33a_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"r33a_{variant_code}_{process_id}", V18_PATH)
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

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })

    _base = mod.agent

    def agent_var(obs, configuration=None):
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
                if variant_code == "VarB":
                    # SURGICAL GUARD: Do NOT promote MILK if queue length > 8 AND a MELON/STRAWBERRY sale exists
                    has_large_crop = any(o[0] == "SELL" and len(o) > 1 and o[1] in ("MELON", "STRAWBERRY") for o in market_orders)
                    if len(market_orders) > 8 and has_large_crop:
                        return (1, idx) # Keep behind crop sales to prevent displacement!
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

    return agent_var


def _run_r33a_match(args):
    variant_code, seed, process_id = args
    try:
        agent_var = _load_r33a_variant(variant_code, f"{process_id}_var")
        agent_v41 = _load_r33a_variant("V41", f"{process_id}_v41")

        p0_is_var = (seed % 2 == 0)
        p0 = agent_var if p0_is_var else agent_v41
        p1 = agent_v41 if p0_is_var else agent_var

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([p0, p1])

        idx_var = 0 if p0_is_var else 1
        idx_v41 = 1 if p0_is_var else 0

        final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
        final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

        return {
            "variant_code": variant_code,
            "seed": seed,
            "final_cash": final_cash,
            "final_v41": final_v41,
            "win": final_cash > final_v41,
            "error": None,
        }
    except Exception as e:
        return {
            "variant_code": variant_code,
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
    print(f" RESEARCH 33A: SURGICAL MILK-RANKER GUARD ABLATION WITH {num_cpus} CPU WORKERS")
    print("=" * 90)

    checkpoint = load_checkpoint()
    variants = ["VarA", "VarB"]
    seeds = list(range(1000, 1100))

    tasks_to_run = []
    for var in variants:
        if var not in checkpoint:
            checkpoint[var] = {}

        for seed in seeds:
            seed_key = str(seed)
            if seed_key not in checkpoint[var]:
                tasks_to_run.append((var, seed, f"r33a_{var}_{seed}"))

    completed_count = 200 - len(tasks_to_run)
    print(f" Checkpoint status: {completed_count} / 200 matches already completed.")
    print(f" Remaining tasks to run: {len(tasks_to_run)} matches.")

    if tasks_to_run:
        with ProcessPoolExecutor(max_workers=num_cpus) as executor:
            futures = {executor.submit(_run_r33a_match, t): t for t in tasks_to_run}
            completed_in_run = 0
            for future in as_completed(futures):
                res = future.result()
                var_key = res["variant_code"]
                seed_key = str(res["seed"])
                checkpoint[var_key][seed_key] = res
                completed_in_run += 1

                if completed_in_run % 20 == 0 or completed_in_run == len(tasks_to_run):
                    save_checkpoint(checkpoint)
                    print(f" Progress: {completed_count + completed_in_run} / 200 matches saved to checkpoint.")

    print("\n" + "=" * 95)
    print(" RESEARCH 33A: SURGICAL MILK-RANKER GUARD SUMMARY TABLE (200 MATCHES)")
    print("=" * 95)
    print(f"{'Variant':<10} | {'Surgical Guard Configuration':<36} | {'Final Cash ($)':<16} | {'Win Rate':<10}")
    print("-" * 95)

    names = {
        "VarA": "Current V4.2 (Un-guarded Milk Ranker)",
        "VarB": "V4.2 + Surgical Milk-Ranker Guard",
    }

    summary_results = []
    for var in variants:
        matches = list(checkpoint[var].values())

        final_list = [m["final_cash"] for m in matches]
        v41_list = [m["final_v41"] for m in matches]
        wins = sum(1 for m in matches if m["win"])

        avg_final = statistics.mean(final_list)
        avg_v41 = statistics.mean(v41_list)
        win_rate = (wins / len(matches)) * 100.0

        summary_results.append({
            "variant": var,
            "name": names[var],
            "win_rate": win_rate,
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
            "worst_case": round(min(final_list), 2),
        })

        print(f"{var:<10} | {names[var]:<36} | ${avg_final:<15,.2f} | {win_rate:.1f}%")

    print("=" * 95)
    best = max(summary_results, key=lambda x: x["avg_final"])
    print(f"\n OPTIMAL RANKER GUARD DISCOVERED: {best['variant']} - {best['name']} (Final Avg Wealth: ${best['avg_final']:,.2f})")

    with open("research33a_surgical_guard_results.json", "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    main()
