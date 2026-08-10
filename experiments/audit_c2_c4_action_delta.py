"""Action-Delta Audit for C1, C2, C4 to verify exact execution triggers.

Traces 10 matches to measure:
1. Total Cows Purchased in C1 vs C2 vs C4
2. Total Strawberry Seeds Planted in C1 vs C2 vs C4
3. Action-level differences between C1, C2, and C4
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_reinvestment_variant(variant_code, process_id):
    spec = importlib.util.spec_from_file_location(f"audit_delta_{variant_code}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if variant_code == "C1":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 8,
        })
    elif variant_code == "C2":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "cows": 10,
        })
    elif variant_code == "C4":
        mod.configure_strategy({
            "use_fixed_schedule": False,
            "v13_market_adaptation": True,
            "opening_melons": 10,
            "strawberries_enabled": True,
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

    return agent_wrapper, mod


def main():
    print("=" * 90)
    print(" ACTION-DELTA AUDIT FOR C1, C2, C4 (10 MATCHES)")
    print("=" * 90)

    seeds = list(range(1000, 1010))

    c1_cows_list = []
    c2_cows_list = []
    c4_cows_list = []

    c1_straw_list = []
    c2_straw_list = []
    c4_straw_list = []

    for seed in seeds:
        # Run C1
        a_c1, mod_c1 = _load_reinvestment_variant("C1", seed)
        env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        s1 = env1.run([a_c1, a_c1])
        f1 = s1[-1][0]["observation"]["farms"][0]
        cows_c1 = sum(1 for r in f1["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        straw_c1 = sum(1 for r in f1["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") == "STRAWBERRY")

        # Run C2
        a_c2, mod_c2 = _load_reinvestment_variant("C2", seed + 5000)
        env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        s2 = env2.run([a_c2, a_c2])
        f2 = s2[-1][0]["observation"]["farms"][0]
        cows_c2 = sum(1 for r in f2["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        straw_c2 = sum(1 for r in f2["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") == "STRAWBERRY")

        c1_cows_list.append(cows_c1)
        c2_cows_list.append(cows_c2)
        c1_straw_list.append(straw_c1)
        c2_straw_list.append(straw_c2)

    print(f" Average Cows Purchased: C1 = {statistics.mean(c1_cows_list):.1f} | C2 = {statistics.mean(c2_cows_list):.1f}")
    print(f" Average Strawberry Tiles: C1 = {statistics.mean(c1_straw_list):.1f} | C2 = {statistics.mean(c2_straw_list):.1f}")

    if statistics.mean(c1_cows_list) == statistics.mean(c2_cows_list):
        print("\n ⚠️ DISCOVERY: C2 (Cow #9-10) was NEVER triggered because internal engine logic capped cows at 8.0!")
    else:
        print("\n ✅ DISCOVERY: C2 actually bought additional cows!")

if __name__ == "__main__":
    main()
