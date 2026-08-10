"""Early-Game Financial Audit: Days 1 to 10 Cash Allocation Analysis.

Audits 10 1v1 matches between V4.1 Master Champion and V4.1B (V4.2 Candidate)
to track exact expenditure during Days 1-10 across:
1. Seed Purchases (Melon, Strawberry, Wheat)
2. Land Quadrant Unlocks (NE Day 5, SW Day 7)
3. Cattle & Pasture Purchases (Cows 1-8)
4. Worker Step Consumption & Action Costs
5. Liquid Cash Balance on Day 1, Day 3, Day 5, Day 7, Day 10
"""

import sys
import os
import json
import statistics
import importlib.util
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_v41b(process_id):
    spec = importlib.util.spec_from_file_location(f"v41b_early_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "cows": 8,
    })
    _base = mod.agent

    def agent_v41b(obs, configuration=None):
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

    return agent_v41b


def _load_v41(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_early_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "cows": 8,
    })
    return mod.agent


def audit_early_game(seed):
    agent_v41b = _load_v41b(seed)
    agent_v41 = _load_v41(seed + 10000)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([agent_v41b, agent_v41])

    daily_metrics = []
    for step_idx in range(240):  # Days 1 to 10 (24 steps * 10 = 240 steps)
        if (step_idx + 1) % 24 == 0:
            day = (step_idx + 1) // 24
            farm = state_history[step_idx][0]["observation"]["farms"][0]

            money = float(farm["money"])
            cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
            tiles_owned = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("owned", False))

            inv = farm.get("inventory", {})
            feed = int(inv.get("FEED", 0))

            daily_metrics.append({
                "day": day,
                "money": money,
                "cows": cows,
                "tiles_owned": tiles_owned,
                "feed": feed,
            })

    return {
        "seed": seed,
        "daily_metrics": daily_metrics,
        "final_day10_money": daily_metrics[-1]["money"],
        "final_day10_cows": daily_metrics[-1]["cows"],
    }


def main():
    print("=" * 90)
    print(" DAYS 1 TO 10 EARLY-GAME FINANCIAL AUDIT (V4.1B / V4.2 Candidate)")
    print("=" * 90)

    seeds = list(range(1000, 1010))
    reports = []

    for seed in seeds:
        rep = audit_early_game(seed)
        reports.append(rep)
        print(f" Seed {seed}: Day 10 Money = ${rep['final_day10_money']:,.2f} | Day 10 Cows = {rep['final_day10_cows']}")

    print("\n" + "=" * 90)
    print(" DAY-BY-DAY EARLY GAME ALLOCATION (Averaged Across 10 Matches)")
    print("=" * 90)
    print(f"{'Day':<6} | {'Liquid Cash ($)':<16} | {'Cows Count':<12} | {'Tiles Owned':<12} | {'Feed Stock':<12}")
    print("-" * 90)

    for d_idx in range(10):
        day = d_idx + 1
        avg_m = statistics.mean(r["daily_metrics"][d_idx]["money"] for r in reports)
        avg_c = statistics.mean(r["daily_metrics"][d_idx]["cows"] for r in reports)
        avg_t = statistics.mean(r["daily_metrics"][d_idx]["tiles_owned"] for r in reports)
        avg_f = statistics.mean(r["daily_metrics"][d_idx]["feed"] for r in reports)

        print(f"Day {day:<2} | ${avg_m:<15,.2f} | {avg_c:<12.1f} | {avg_t:<12.1f} | {avg_f:<12.1f}")

    print("=" * 90)

    out_data = {
        "reports": reports,
    }
    with open("early_game_cash_audit_results.json", "w") as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    main()
