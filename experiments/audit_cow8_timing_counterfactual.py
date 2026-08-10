"""Cow #8 Purchase Timing Counterfactual Audit (Telemetry Pre-Screening on 10 Seeds).

Traces 10 competitive 1v1 matches across Seeds 1000-1009 comparing 5 Cow #8 Purchase Timing Variants:
- Control: Buy Cow #8 naturally at V4.2 timing (Day 16)
- Variant A: Buy Cow #8 as soon as cash >= $300 (Days 12-13)
- Variant B: Buy Cow #8 1 day earlier (Day 15)
- Variant C: Buy Cow #8 2 days earlier (Day 14)
- Variant D: Buy Cow #8 3 days earlier (Day 13)

Telemetry Tracked:
1. Day Cow #8 is Purchased
2. Total Milk Revenue ($)
3. Day 20 Crop Investment Cash ($)
4. Final Average Wealth ($)
5. Win Rate vs V4.1 Master Champion (%)
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_cow8_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"c8_{variant_code}_{process_id}", V18_PATH)
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

    def agent_cow8(obs, configuration=None):
        # Apply Cow #8 timing override
        if variant_code != "Control":
            farm0 = obs["farms"][0]
            money = float(farm0["money"])
            cows = sum(1 for r in farm0["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
            step = obs["step"]
            day = (step // 24) + 1

            # Check if we need to force Cow #8 purchase earlier
            target_day_map = {"VarA": 12, "VarB": 15, "VarC": 14, "VarD": 13}
            target_day = target_day_map.get(variant_code, 16)

            if cows == 7 and day >= target_day and money >= 300.0:
                action_dict = _base(obs)
                orders = action_dict.get("market", [])
                if not any(o[0] == "BUY_ANIMAL" and len(o) > 1 and o[1] == "COW" for o in orders):
                    action_dict["market"] = [['BUY_ANIMAL', 'COW', 1]] + orders
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

    return agent_cow8, mod


def audit_cow8_seed(variant_code, seed):
    agent_var, mod_var = _load_cow8_variant(variant_code, f"{seed}_{variant_code}")
    agent_v41, mod_v41 = _load_cow8_variant("V41", f"{seed}_v41")

    p0_is_var = (seed % 2 == 0)
    p0 = agent_var if p0_is_var else agent_v41
    p1 = agent_v41 if p0_is_var else agent_var

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_var = 0 if p0_is_var else 1
    idx_v41 = 1 if p0_is_var else 0

    # Trace Cow #8 purchase step
    cow8_step = None
    for step_i in range(720):
        f = state_history[step_i][idx_var]["observation"]["farms"][idx_var]
        cows = sum(1 for r in f["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        if cows == 8:
            cow8_step = step_i
            break

    cow8_day = ((cow8_step // 24) + 1) if cow8_step is not None else 30

    final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
    final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

    return {
        "variant": variant_code,
        "seed": seed,
        "cow8_day": cow8_day,
        "final_cash": final_cash,
        "final_v41": final_v41,
        "win": final_cash > final_v41,
    }


def main():
    print("=" * 95)
    print(" COW #8 TIMING COUNTERFACTUAL AUDIT (TELEMETRY PRE-SCREENING ON 10 SEEDS)")
    print("=" * 95)

    variants = ["Control", "VarA", "VarB", "VarC", "VarD"]
    seeds = list(range(1000, 1010))

    summary = []
    for var in variants:
        results = [audit_cow8_seed(var, s) for s in seeds]

        avg_cow8_day = statistics.mean(r["cow8_day"] for r in results)
        avg_final = statistics.mean(r["final_cash"] for r in results)
        avg_v41 = statistics.mean(r["final_v41"] for r in results)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "variant": var,
            "avg_cow8_day": round(avg_cow8_day, 1),
            "win_rate": win_rate,
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        print(f" Variant {var:<7} | Avg Cow #8 Day: {avg_cow8_day:<5.1f} | Final Cash: ${avg_final:<12,.2f} | Win Rate: {win_rate:.1f}%")

    print("=" * 95)

    with open("cow8_timing_counterfactual_results.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
