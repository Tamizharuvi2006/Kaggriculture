"""Day 8 to Day 15 Decision & Allocation Audit.

Compares 10-Melon Strategy (P2A) vs 15-Melon Strategy (P1 Baseline) across Days 8 to 15
to solve the mystery:
Why does 15 Melons have MORE wealth on Day 15 ($11.9k vs $8.8k), but finish -$9.5k poorer on Day 30 ($86.6k vs $96.1k)?

Audits across Days 8-15:
1. Quadrant Unlocks (NE, SW, SE land unlocks)
2. Cow Fleet Expansion (Cows 2-8 purchase days)
3. Crop Re-planting (Melon vs Strawberry vs Wheat vs Feed)
4. Feed Inventory Purchases ($)
5. Liquid Cash Reserves & Unsold Inventory on Day 15 ($)
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


def _load_audit_agent(melon_count, process_id):
    spec = importlib.util.spec_from_file_location(f"audit_{melon_count}_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": melon_count,
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


def audit_match_days8_15(seed):
    agent_10 = _load_audit_agent(10, f"m10_{seed}")
    agent_15 = _load_audit_agent(15, f"m15_{seed}")

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([agent_10, agent_15])

    # Trace steps 191 (Day 8) to 359 (Day 15)
    metrics_10 = []
    metrics_15 = []

    for day in range(8, 16):
        step_idx = day * 24 - 1
        f10 = state_history[step_idx][0]["observation"]["farms"][0]
        f15 = state_history[step_idx][1]["observation"]["farms"][1]

        def extract_farm_stats(farm):
            m = float(farm["money"])
            cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
            tiles = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("owned", False))
            inv = farm.get("inventory", {})
            feed = int(inv.get("FEED", 0))
            milk = int(inv.get("MILK", 0))
            melons = int(inv.get("MELON", 0))
            strawberries = int(inv.get("STRAWBERRY", 0))
            
            # Count growing crops by type
            growing_melons = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") == "MELON")
            growing_straw = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") == "STRAWBERRY")

            return {
                "day": day,
                "money": m,
                "cows": cows,
                "tiles_owned": tiles,
                "feed": feed,
                "milk": milk,
                "melons": melons,
                "strawberries": strawberries,
                "growing_melons": growing_melons,
                "growing_strawberries": growing_straw,
            }

        metrics_10.append(extract_farm_stats(f10))
        metrics_15.append(extract_farm_stats(f15))

    final_10 = float(state_history[-1][0]["observation"]["farms"][0]["money"])
    final_15 = float(state_history[-1][1]["observation"]["farms"][1]["money"])

    return {
        "seed": seed,
        "metrics_10": metrics_10,
        "metrics_15": metrics_15,
        "final_10": final_10,
        "final_15": final_15,
    }


def main():
    print("=" * 95)
    print(" DAY 8 TO DAY 15 DECISION & ALLOCATION AUDIT (10 MELONS VS 15 MELONS)")
    print("=" * 95)

    seeds = list(range(1000, 1010))
    reports = [audit_match_days8_15(s) for s in seeds]

    print(f"\n{'Day':<5} | {'10-Melon Cash':<14} | {'15-Melon Cash':<14} | {'10 Cows':<8} | {'15 Cows':<8} | {'10 Growing Melons':<18} | {'15 Growing Melons':<18}")
    print("-" * 95)

    for idx in range(8):
        day = idx + 8
        avg_m10 = statistics.mean(r["metrics_10"][idx]["money"] for r in reports)
        avg_m15 = statistics.mean(r["metrics_15"][idx]["money"] for r in reports)
        avg_c10 = statistics.mean(r["metrics_10"][idx]["cows"] for r in reports)
        avg_c15 = statistics.mean(r["metrics_15"][idx]["cows"] for r in reports)
        avg_gm10 = statistics.mean(r["metrics_10"][idx]["growing_melons"] for r in reports)
        avg_gm15 = statistics.mean(r["metrics_15"][idx]["growing_melons"] for r in reports)

        print(f"Day {day:<2} | ${avg_m10:<13,.2f} | ${avg_m15:<13,.2f} | {avg_c10:<8.1f} | {avg_c15:<8.1f} | {avg_gm10:<18.1f} | {avg_gm15:<18.1f}")

    print("=" * 95)

    avg_f10 = statistics.mean(r["final_10"] for r in reports)
    avg_f15 = statistics.mean(r["final_15"] for r in reports)
    print(f" Final Day 30 Wealth: 10-Melon Avg = ${avg_f10:,.2f} vs 15-Melon Avg = ${avg_f15:,.2f} (Gap: +${avg_f10 - avg_f15:,.2f})")
    print("=" * 95)

    with open("audit_days8_15_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
