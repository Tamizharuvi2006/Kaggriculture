"""Phase C: Worker / Action Economics Audit (Days 15 to 30) - Fixed Inspector.

Traces 5 competitive 1v1 seeds (1000 to 1004) turn-by-turn from Day 15 (Step 360) to Day 30 (Step 720).
Categorizes every single worker action into 8 precise activity categories:
1. MILKING: Milking cows in pasture
2. FEEDING: Feeding cattle / delivering feed to troughs
3. HARVESTING: Harvesting mature crops from fields
4. PLANTING_WATERING: Planting seeds or watering fields
5. SELLING: Delivering goods to market slots
6. WALKING: Grid transit steps between locations
7. IDLE: Sitting idle with no active task
8. OTHER: Clearing / building / maintenance

Measures action percentages, walking overhead, and worker action capacity limits.
Zero code modifications made.
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_v42(process_id):
    spec = importlib.util.spec_from_file_location(f"v42_pc2_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

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

    return agent_v42


def _load_v41(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_pc2_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_phase_c_seed(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1

    action_counts = {
        "MILKING": 0,
        "FEEDING": 0,
        "HARVESTING": 0,
        "PLANTING_WATERING": 0,
        "SELLING": 0,
        "WALKING": 0,
        "IDLE": 0,
        "OTHER": 0,
    }

    total_worker_steps = 0

    for s_idx in range(360, 720):
        obs_step = state_history[s_idx]
        a_v42 = obs_step[idx_v42].get("action", {})
        
        # In Kaggle Agriculture, worker actions are stored in action["workers"] dictionary or list
        w_acts = a_v42.get("workers", {}) if isinstance(a_v42, dict) else {}
        
        if isinstance(w_acts, dict):
            worker_items = list(w_acts.items())
        elif isinstance(w_acts, list):
            worker_items = list(enumerate(w_acts))
        else:
            worker_items = []

        # If no worker actions in action, count 6 workers as IDLE for that step
        if not worker_items:
            action_counts["IDLE"] += 6
            total_worker_steps += 6
            continue

        for w_id, w_act in worker_items:
            total_worker_steps += 1
            act_name = ""
            if isinstance(w_act, dict):
                act_name = str(w_act.get("type", "")).upper()
            elif isinstance(w_act, (list, tuple)) and len(w_act) > 0:
                act_name = str(w_act[0]).upper()
            elif isinstance(w_act, str):
                act_name = w_act.upper()

            if "MILK" in act_name:
                action_counts["MILKING"] += 1
            elif "FEED" in act_name:
                action_counts["FEEDING"] += 1
            elif "HARVEST" in act_name:
                action_counts["HARVESTING"] += 1
            elif any(k in act_name for k in ("PLANT", "WATER", "TILL", "SEED")):
                action_counts["PLANTING_WATERING"] += 1
            elif "SELL" in act_name:
                action_counts["SELLING"] += 1
            elif any(k in act_name for k in ("MOVE", "WALK", "GOTO", "PATH")):
                action_counts["WALKING"] += 1
            elif any(k in act_name for k in ("IDLE", "WAIT", "NONE", "")):
                action_counts["IDLE"] += 1
            else:
                action_counts["OTHER"] += 1

    return {
        "seed": seed,
        "total_worker_steps": total_worker_steps,
        "action_counts": action_counts,
    }


def main():
    print("=" * 95)
    print(" PHASE C: WORKER / ACTION ECONOMICS AUDIT (DAYS 15 TO 30)")
    print("=" * 95)

    seeds = list(range(1000, 1005))
    reports = [audit_phase_c_seed(s) for s in seeds]

    tot_steps = sum(r["total_worker_steps"] for r in reports)

    aggregated = {
        "MILKING": sum(r["action_counts"]["MILKING"] for r in reports),
        "FEEDING": sum(r["action_counts"]["FEEDING"] for r in reports),
        "HARVESTING": sum(r["action_counts"]["HARVESTING"] for r in reports),
        "PLANTING_WATERING": sum(r["action_counts"]["PLANTING_WATERING"] for r in reports),
        "SELLING": sum(r["action_counts"]["SELLING"] for r in reports),
        "WALKING": sum(r["action_counts"]["WALKING"] for r in reports),
        "IDLE": sum(r["action_counts"]["IDLE"] for r in reports),
        "OTHER": sum(r["action_counts"]["OTHER"] for r in reports),
    }

    print(f"\n Total Worker Actions Analyzed (Days 15-30 across 5 seeds): {tot_steps} steps")
    print("-" * 95)
    print(f"{'Activity Category':<25} | {'Action Count':<14} | {'Percentage of Worker Time':<25}")
    print("-" * 95)

    for cat, cnt in sorted(aggregated.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / max(1, tot_steps)) * 100.0
        print(f" {cat:<24} | {cnt:<14} | {pct:.2f}%")

    print("=" * 95)

    with open("phase_c_worker_action_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
