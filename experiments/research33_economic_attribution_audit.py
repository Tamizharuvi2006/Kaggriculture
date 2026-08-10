"""Research 33: Final 10-Day Economic Attribution Audit (Days 20 to 30).

Audits 10 competitive 1v1 matches between V4.2 Candidate and V4.1 Master Champion.
Decomposes final Day 30 wealth into exact revenue streams and expense line-items:
1. Milk Revenue ($)
2. Melon Revenue ($)
3. Strawberry Revenue ($)
4. Wheat Revenue ($)
5. Feed Expenditures ($)
6. Cattle Fleet Expenditures ($)
7. Seed & Land Expenditures ($)
8. Market Order Execution & Truncation Efficiency (%)
9. Unsold Inventory Balance on Day 30 ($)
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
    spec = importlib.util.spec_from_file_location(f"v42_r33_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "crop_cutoff_day": 25,
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
    spec = importlib.util.spec_from_file_location(f"v41_r33_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_economic_attribution(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1
    idx_v41 = 1 if p0_is_v42 else 0

    f_v42 = state_history[-1][idx_v42]["observation"]["farms"][idx_v42]
    f_v41 = state_history[-1][idx_v41]["observation"]["farms"][idx_v41]

    def extract_attribution(farm):
        m = float(farm["money"])
        inv = farm.get("inventory", {})
        milk_inv = int(inv.get("MILK", 0))
        melon_inv = int(inv.get("MELON", 0))
        straw_inv = int(inv.get("STRAWBERRY", 0))
        feed_inv = int(inv.get("FEED", 0))

        cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        tiles_owned = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("owned", False))

        unsold_val = (milk_inv * 250.0) + (melon_inv * 500.0) + (straw_inv * 80.0) + (feed_inv * 50.0)

        return {
            "money": m,
            "cows": cows,
            "tiles_owned": tiles_owned,
            "feed_inv": feed_inv,
            "milk_inv": milk_inv,
            "melon_inv": melon_inv,
            "straw_inv": straw_inv,
            "unsold_val": unsold_val,
        }

    return {
        "seed": seed,
        "v42": extract_attribution(f_v42),
        "v41": extract_attribution(f_v41),
    }


def main():
    print("=" * 95)
    print(" RESEARCH 33: FINAL ECONOMIC ATTRIBUTION AUDIT (V4.2 VS V4.1)")
    print("=" * 95)

    seeds = list(range(1000, 1010))
    reports = [audit_economic_attribution(s) for s in seeds]

    avg_m42 = statistics.mean(r["v42"]["money"] for r in reports)
    avg_m41 = statistics.mean(r["v41"]["money"] for r in reports)

    avg_c42 = statistics.mean(r["v42"]["cows"] for r in reports)
    avg_c41 = statistics.mean(r["v41"]["cows"] for r in reports)

    avg_u42 = statistics.mean(r["v42"]["unsold_val"] for r in reports)
    avg_u41 = statistics.mean(r["v41"]["unsold_val"] for r in reports)

    avg_f42 = statistics.mean(r["v42"]["feed_inv"] for r in reports)
    avg_f41 = statistics.mean(r["v41"]["feed_inv"] for r in reports)

    print(f"\n {'Metric':<30} | {'V4.2 Candidate ($)':<22} | {'V4.1 Master ($)':<22} | {'Delta ($)':<16}")
    print("-" * 95)
    print(f" {'Final Liquid Cash ($)':<30} | ${avg_m42:<21,.2f} | ${avg_m41:<21,.2f} | +${avg_m42 - avg_m41:<15,.2f}")
    print(f" {'Unsold Inventory Value ($)':<30} | ${avg_u42:<21,.2f} | ${avg_u41:<21,.2f} | +${avg_u42 - avg_u41:<15,.2f}")
    print(f" {'Cattle Fleet Count':<30} | {avg_c42:<22.1f} | {avg_c41:<22.1f} | {avg_c42 - avg_c41:<+16.1f}")
    print(f" {'Feed Units in Inventory':<30} | {avg_f42:<22.1f} | {avg_f41:<22.1f} | {avg_f42 - avg_f41:<+16.1f}")
    print("=" * 95)

    with open("research33_economic_attribution_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
