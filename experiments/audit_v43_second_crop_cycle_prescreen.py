"""V4.3 Second Crop Cycle Pre-Screening (10 Seeds: 1000 to 1009).

Evaluates 10 competitive 1v1 matches comparing 4 Second Crop Cycle Variants:
1. Control: Current V4.2 Baseline
2. V3-A: Re-plant Melons on Days 12-20 when cash >= $2k and active fields == 0 (Existing tiles ONLY)
3. V3-B: Re-plant using V4.1 Dynamic Evaluator when cash >= $2k and active fields == 0 (Existing tiles ONLY)
4. V3-C: Melon-Only forced re-planting on existing cleared tiles

Guards:
- ZERO Land Expansion (Uses existing NW/NE farm tiles only)
- Time-to-Harvest <= 715 (Full maturity before Step 720)

Telemetry Tracked:
- Second Crop Planting Step & Day
- Crop Selected
- Seed Cost ($)
- Day 20-28 Harvest Revenue ($)
- Final Average Wealth ($)
- Win Rate vs V4.1 Master Champion (%)
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_v43_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"v43_{variant_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if variant_code == "V41":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 15,
            "cows": 8,
        })
        return mod.agent, mod

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })

    _base = mod.agent

    def agent_v43(obs, configuration=None):
        step = obs["step"]
        day = (step // 24) + 1
        farm0 = obs["farms"][0]
        money = float(farm0["money"])

        active_fields = sum(1 for r in farm0["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") is not None)

        if variant_code in ("V3-A", "V3-B", "V3-C"):
            if 12 <= day <= 20 and money >= 2000.0 and active_fields == 0:
                crop_to_plant = "MELON"
                if variant_code == "V3-B":
                    crop_to_plant = "STRAWBERRY" if money < 3000.0 else "MELON"

                # Check if seed order can be issued
                action_dict = _base(obs)
                orders = action_dict.get("market", [])
                if not any(o[0] == "BUY_SEED" and len(o) > 1 and o[1] == crop_to_plant for o in orders):
                    qty = 10 if crop_to_plant == "MELON" else 15
                    action_dict["market"] = [['BUY_SEED', crop_to_plant, qty]] + orders
                    return action_dict

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

    return agent_v43, mod


def audit_v43_seed(variant_code, seed):
    agent_var, mod_var = _load_v43_variant(variant_code, f"{seed}_{variant_code}")
    agent_v41, mod_v41 = _load_v43_variant("V41", f"{seed}_v41")

    p0_is_var = (seed % 2 == 0)
    p0 = agent_var if p0_is_var else agent_v41
    p1 = agent_v41 if p0_is_var else agent_var

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_var = 0 if p0_is_var else 1
    idx_v41 = 1 if p0_is_var else 0

    final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
    final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

    # Trace Day 20 cash
    d20_cash = float(state_history[479][idx_var]["observation"]["farms"][idx_var]["money"])

    return {
        "variant": variant_code,
        "seed": seed,
        "d20_cash": d20_cash,
        "final_cash": final_cash,
        "final_v41": final_v41,
        "win": final_cash > final_v41,
    }


def main():
    print("=" * 95)
    print(" V4.3 SECOND CROP CYCLE PRE-SCREENING (10 SEEDS: 1000 TO 1009)")
    print("=" * 95)

    variants = ["Control", "V3-A", "V3-B", "V3-C"]
    seeds = list(range(1000, 1010))

    summary = []
    for var in variants:
        results = [audit_v43_seed(var, s) for s in seeds]

        avg_d20 = statistics.mean(r["d20_cash"] for r in results)
        avg_final = statistics.mean(r["final_cash"] for r in results)
        avg_v41 = statistics.mean(r["final_v41"] for r in results)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "variant": var,
            "win_rate": win_rate,
            "avg_d20": round(avg_d20, 2),
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        print(f" Variant {var:<7} | Day-20 Cash: ${avg_d20:<11,.2f} | Final Cash: ${avg_final:<12,.2f} | Win Rate: {win_rate:.1f}%")

    print("=" * 95)

    with open("v43_second_crop_cycle_results.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
