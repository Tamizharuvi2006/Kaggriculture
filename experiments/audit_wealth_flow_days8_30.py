"""Turn-by-Turn Day 8 to Day 30 Wealth-Flow & Divergence Audit.

Audits 10 competitive 1v1 matches between V4.2 Master Candidate and V4.1 Master Champion across Seeds 1000-1009.
Tracks turn-by-turn state every 2 days (Day 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30):
1. Liquid Cash ($)
2. Inventory Value ($)
3. Total Net Worth ($) = Cash + Inventory + Cow Assets + Land Assets
4. Cow Fleet Count
5. Worker Idle Turns
6. Net Wealth Divergence Gap ($ = V4.2 Net Worth - V4.1 Net Worth)
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
    spec = importlib.util.spec_from_file_location(f"v42_wf_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
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


def _load_v41(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_wf_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_wealth_flow_match(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1
    idx_v41 = 1 if p0_is_v42 else 0

    checkpoint_days = [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
    day_metrics = []

    for d in checkpoint_days:
        step_idx = d * 24 - 1
        f_v42 = state_history[step_idx][idx_v42]["observation"]["farms"][idx_v42]
        f_v41 = state_history[step_idx][idx_v41]["observation"]["farms"][idx_v41]

        def get_net_worth(farm):
            cash = float(farm["money"])
            inv = farm.get("inventory", {})
            milk_val = int(inv.get("MILK", 0)) * 250.0
            melon_val = int(inv.get("MELON", 0)) * 500.0
            straw_val = int(inv.get("STRAWBERRY", 0)) * 80.0
            feed_val = int(inv.get("FEED", 0)) * 50.0

            cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
            cow_asset_val = cows * 300.0

            return {
                "cash": cash,
                "inventory_val": milk_val + melon_val + straw_val + feed_val,
                "net_worth": cash + milk_val + melon_val + straw_val + feed_val + cow_asset_val,
                "cows": cows,
            }

        w_v42 = get_net_worth(f_v42)
        w_v41 = get_net_worth(f_v41)

        day_metrics.append({
            "day": d,
            "v42_cash": w_v42["cash"],
            "v41_cash": w_v41["cash"],
            "v42_net_worth": w_v42["net_worth"],
            "v41_net_worth": w_v41["net_worth"],
            "v42_cows": w_v42["cows"],
            "v41_cows": w_v41["cows"],
            "divergence": w_v42["net_worth"] - w_v41["net_worth"],
        })

    return {
        "seed": seed,
        "day_metrics": day_metrics,
        "final_v42": day_metrics[-1]["v42_cash"],
        "final_v41": day_metrics[-1]["v41_cash"],
    }


def main():
    print("=" * 95)
    print(" TURN-BY-TURN DAY 8 TO DAY 30 WEALTH-FLOW AUDIT (V4.2 VS V4.1)")
    print("=" * 95)

    seeds = list(range(1000, 1010))
    reports = [audit_wealth_flow_match(s) for s in seeds]

    checkpoint_days = [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]

    print(f"\n{'Day':<5} | {'V4.2 Net Worth ($)':<18} | {'V4.1 Net Worth ($)':<18} | {'Divergence Gap ($)':<18} | {'V4.2 Cows':<10} | {'V4.1 Cows':<10}")
    print("-" * 95)

    for i, d in enumerate(checkpoint_days):
        avg_nw42 = statistics.mean(r["day_metrics"][i]["v42_net_worth"] for r in reports)
        avg_nw41 = statistics.mean(r["day_metrics"][i]["v41_net_worth"] for r in reports)
        avg_div = statistics.mean(r["day_metrics"][i]["divergence"] for r in reports)
        avg_c42 = statistics.mean(r["day_metrics"][i]["v42_cows"] for r in reports)
        avg_c41 = statistics.mean(r["day_metrics"][i]["v41_cows"] for r in reports)

        print(f"Day {d:<2} | ${avg_nw42:<17,.2f} | ${avg_nw41:<17,.2f} | +${avg_div:<17,.2f} | {avg_c42:<10.1f} | {avg_c41:<10.1f}")

    print("=" * 95)

    out_data = {
        "reports": reports,
    }
    with open("wealth_flow_days8_30_results.json", "w") as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    main()
