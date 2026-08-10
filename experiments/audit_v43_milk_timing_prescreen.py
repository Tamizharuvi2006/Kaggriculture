"""V4.3 Milk Selling Timing Pre-Screening (10 Seeds: 1000 to 1009).

Evaluates 10 competitive 1v1 matches comparing 4 Milk Selling Timing Variants:
1. Control: Current V4.2 Baseline (Immediate sell when price >= $230)
2. Variant A: Defer Milk sale by 1 step if price < $250 & Feed Runway > 3 steps (Max Hold = 1 step)
3. Variant B: Defer Milk sale by 2 steps if price < $250 & Feed Runway > 3 steps (Max Hold = 2 steps)
4. Variant C: Hold until price >= $270 with Hard Max Hold = 2 steps & Feed Runway Guard > 3 steps

Guards:
- HARD MAX HOLD = 1 to 2 steps (Prevents capital lockup)
- FEED RUNWAY GUARD = If cash < $500 or Feed Runway < 3 steps, IMMEDIATELY sell Milk

Telemetry Tracked:
- Average Milk Selling Price ($)
- Total Milk Revenue ($)
- Cash Trajectory & Feed Expenditures ($)
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


def _load_v43_milk_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"v43m_{variant_code}_{process_id}", V18_PATH)
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
    hold_tracker = {} # Tracks step count milk has been held

    def agent_milk_timing(obs, configuration=None):
        step = obs["step"]
        farm0 = obs["farms"][0]
        money = float(farm0["money"])
        feed_inv = int(farm0.get("inventory", {}).get("FEED", 0))

        prices = mod._get(mod._get(obs, "market", {}), "prices", {}) or {}
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

        action_dict = _base(obs)
        market_orders = action_dict.get("market", [])
        if not market_orders:
            return action_dict

        if variant_code != "Control":
            # Check Milk Hold Rules
            curr_hold = hold_tracker.get("milk_hold", 0)

            # Safety Guard: If cash < 500 or feed_inv < 3, force immediate sale
            safety_override = (money < 500.0 or feed_inv < 3)

            defer_sale = False

            if not safety_override:
                if variant_code == "VarA" and milk_p < 250.0 and curr_hold < 1:
                    defer_sale = True
                elif variant_code == "VarB" and milk_p < 250.0 and curr_hold < 2:
                    defer_sale = True
                elif variant_code == "VarC" and milk_p < 270.0 and curr_hold < 2:
                    defer_sale = True

            if defer_sale:
                hold_tracker["milk_hold"] = curr_hold + 1
                # Filter out SELL MILK orders for this step
                filtered = [o for o in market_orders if not (o[0] == "SELL" and len(o) > 1 and o[1] == "MILK")]
                action_dict["market"] = filtered
                return action_dict
            else:
                hold_tracker["milk_hold"] = 0

        # Apply standard Ranker ordering
        if len(market_orders) > 1:
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

    return agent_milk_timing, mod


def audit_v43_milk_seed(variant_code, seed):
    agent_var, mod_var = _load_v43_milk_variant(variant_code, f"{seed}_{variant_code}")
    agent_v41, mod_v41 = _load_v43_milk_variant("V41", f"{seed}_v41")

    p0_is_var = (seed % 2 == 0)
    p0 = agent_var if p0_is_var else agent_v41
    p1 = agent_v41 if p0_is_var else agent_var

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_var = 0 if p0_is_var else 1
    idx_v41 = 1 if p0_is_var else 0

    final_cash = float(state_history[-1][idx_var]["observation"]["farms"][idx_var]["money"])
    final_v41 = float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"])

    # Audit Days 15-30 Milk Selling Price & Revenue
    total_milk_sold = 0
    total_milk_rev = 0.0
    milk_prices = []

    for s_idx in range(360, 720):
        obs_step = state_history[s_idx]
        a_var = obs_step[idx_var].get("action", {})
        m_var = a_var.get("market", []) if isinstance(a_var, dict) else []

        prices = obs_step[idx_var]["observation"].get("market", {}).get("prices", {})
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)
        milk_prices.append(milk_p)

        for ord_item in m_var:
            if ord_item[0] == "SELL" and len(ord_item) > 1 and ord_item[1] == "MILK":
                qty = ord_item[2] if len(ord_item) > 2 else 1
                total_milk_sold += qty
                total_milk_rev += qty * milk_p

    return {
        "variant": variant_code,
        "seed": seed,
        "avg_milk_price": statistics.mean(milk_prices),
        "milk_rev": total_milk_rev,
        "final_cash": final_cash,
        "final_v41": final_v41,
        "win": final_cash > final_v41,
    }


def main():
    print("=" * 95)
    print(" V4.3 MILK SELLING TIMING PRE-SCREENING (10 SEEDS: 1000 TO 1009)")
    print("=" * 95)

    variants = ["Control", "VarA", "VarB", "VarC"]
    seeds = list(range(1000, 1010))

    summary = []
    for var in variants:
        results = [audit_v43_milk_seed(var, s) for s in seeds]

        avg_price = statistics.mean(r["avg_milk_price"] for r in results)
        avg_rev = statistics.mean(r["milk_rev"] for r in results)
        avg_final = statistics.mean(r["final_cash"] for r in results)
        avg_v41 = statistics.mean(r["final_v41"] for r in results)
        wins = sum(1 for r in results if r["win"])
        win_rate = (wins / len(results)) * 100.0

        summary.append({
            "variant": var,
            "win_rate": win_rate,
            "avg_price": round(avg_price, 2),
            "avg_rev": round(avg_rev, 2),
            "avg_final": round(avg_final, 2),
            "avg_v41": round(avg_v41, 2),
            "margin": round(avg_final - avg_v41, 2),
        })

        print(f" Variant {var:<7} | Avg Milk Price: ${avg_price:<6.2f} | Milk Rev: ${avg_rev:<10,.2f} | Final Cash: ${avg_final:<11,.2f} | Win Rate: {win_rate:.1f}%")

    print("=" * 95)

    with open("v43_milk_timing_results.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
