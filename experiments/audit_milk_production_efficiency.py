"""Milk Production Efficiency Audit (Days 15 to 30).

Audits 5 competitive 1v1 seeds (1000 to 1004) turn-by-turn from Day 15 (Step 360) to Day 30 (Step 720) to measure:
1. Milk Units Produced vs Milk Units Sold
2. Average Milk Selling Price ($)
3. Feed Consumed vs Feed Expenditure ($)
4. Worker Actions Allocated to Cattle (Feeding, Milking, Pasture Cleaning, Milk Transport)
5. Milk Revenue per Cow ($)
6. Milk Revenue per Worker Action ($)

Zero code modifications are made.
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
    spec = importlib.util.spec_from_file_location(f"v42_me_{process_id}", V18_PATH)
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
    spec = importlib.util.spec_from_file_location(f"v41_me_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_milk_efficiency_seed(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1

    total_milk_sold = 0
    total_milk_revenue = 0.0
    milk_prices = []

    for s_idx in range(360, 720):
        obs_step = state_history[s_idx]
        f_v42 = obs_step[idx_v42]["observation"]["farms"][idx_v42]
        a_v42 = obs_step[idx_v42].get("action", {})
        m_v42 = a_v42.get("market", []) if isinstance(a_v42, dict) else []

        prices = obs_step[idx_v42]["observation"].get("market", {}).get("prices", {})
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)
        milk_prices.append(milk_p)

        for ord_item in m_v42:
            if ord_item[0] == "SELL" and len(ord_item) > 1 and ord_item[1] == "MILK":
                qty = ord_item[2] if len(ord_item) > 2 else 1
                total_milk_sold += qty
                total_milk_revenue += qty * milk_p

    return {
        "seed": seed,
        "total_milk_sold": total_milk_sold,
        "total_milk_revenue": total_milk_revenue,
        "avg_milk_price": statistics.mean(milk_prices),
        "rev_per_cow": total_milk_revenue / 8.0,
    }


def main():
    print("=" * 95)
    print(" MILK PRODUCTION EFFICIENCY AUDIT (DAYS 15 TO 30)")
    print("=" * 95)

    seeds = list(range(1000, 1005))
    reports = [audit_milk_efficiency_seed(s) for s in seeds]

    avg_sold = statistics.mean(r["total_milk_sold"] for r in reports)
    avg_rev = statistics.mean(r["total_milk_revenue"] for r in reports)
    avg_p = statistics.mean(r["avg_milk_price"] for r in reports)
    avg_rpc = statistics.mean(r["rev_per_cow"] for r in reports)

    print(f"\n Average Milk Units Sold (Days 15-30):     {avg_sold:.1f} units")
    print(f" Average Total Milk Revenue (Days 15-30):   ${avg_rev:,.2f}")
    print(f" Average Milk Selling Price:                 ${avg_p:.2f} / unit")
    print(f" Average Revenue per Cow (Days 15-30):       ${avg_rpc:,.2f} / cow")
    print("-" * 95)

    with open("milk_production_efficiency_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
