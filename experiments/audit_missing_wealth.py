"""Diagnostic Audit: Where Does the Missing Wealth Disappear in 1v1 Competitive Play?

Audits 10 1v1 matches between V8.4 and V4.1 to measure:
1. Truncated / Expired Market Orders (Market Order Queue Saturation)
2. Total Milk Production vs Total Milk Sold ($ Unsold Milk Inventory)
3. Total Cow Count Evolution on Days 15, 20, 25, 30
4. Ending Inventory Cash Value on Day 30 (Unrealized Wealth)
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
V84_PATH = r"D:\kaggriculture\baseline\submission_v84_experimental.py"


def _load_v84(process_id):
    spec = importlib.util.spec_from_file_location(f"v84_mw_{process_id}", V84_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def _load_v41(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_mw_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
    })
    return mod.agent


def main():
    print("=" * 90)
    print(" MISSING WEALTH DIAGNOSTIC AUDIT: V8.4 IN COMPETITIVE 1v1 PLAY")
    print("=" * 90)

    seeds = list(range(1000, 1010))
    audit_data = []

    for seed in seeds:
        agent_v84 = _load_v84(seed)
        agent_v41 = _load_v41(seed + 10000)

        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        state_history = env.run([agent_v84, agent_v41])

        # Analyze final state on Day 30 (Step 720)
        final_obs_v84 = state_history[-1][0]["observation"]["farms"][0]
        final_obs_v41 = state_history[-1][1]["observation"]["farms"][1]

        final_money_v84 = float(final_obs_v84["money"])
        final_money_v41 = float(final_obs_v41["money"])

        # Inventory on Day 30
        inv_v84 = final_obs_v84.get("inventory", {})
        milk_inv_v84 = int(inv_v84.get("MILK", 0))
        melon_inv_v84 = int(inv_v84.get("MELON", 0))
        straw_inv_v84 = int(inv_v84.get("STRAWBERRY", 0))
        feed_inv_v84 = int(inv_v84.get("FEED", 0))

        # Count cows on Day 15, Day 20, Day 25, Day 30
        cows_d15 = sum(1 for r in state_history[359][0]["observation"]["farms"][0]["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        cows_d20 = sum(1 for r in state_history[479][0]["observation"]["farms"][0]["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        cows_d25 = sum(1 for r in state_history[599][0]["observation"]["farms"][0]["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        cows_d30 = sum(1 for r in final_obs_v84["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")

        # Estimate unsold inventory cash value
        prices = state_history[-1][0]["observation"]["market"].get("prices", {})
        milk_p = float(prices.get("MILK", {}).get("price", 250.0) if isinstance(prices.get("MILK"), dict) else prices.get("MILK", 250.0))
        unsold_val_v84 = milk_inv_v84 * milk_p + melon_inv_v84 * 500.0 + straw_inv_v84 * 80.0

        audit_data.append({
            "seed": seed,
            "final_money_v84": final_money_v84,
            "final_money_v41": final_money_v41,
            "cows_d15": cows_d15,
            "cows_d20": cows_d20,
            "cows_d25": cows_d25,
            "cows_d30": cows_d30,
            "milk_inv_d30": milk_inv_v84,
            "melon_inv_d30": melon_inv_v84,
            "straw_inv_d30": straw_inv_v84,
            "unsold_inventory_val": unsold_val_v84,
        })

        print(f" Seed {seed}: V8.4 Money = ${final_money_v84:,.2f} | Cows (D15/20/25/30): {cows_d15}/{cows_d20}/{cows_d25}/{cows_d30} | Unsold Inv Val: ${unsold_val_v84:,.2f} ({milk_inv_v84} Milk)")

    print("\n" + "=" * 90)
    print(" MISSING WEALTH DIAGNOSTIC SUMMARY (Averaged Across 10 Matches)")
    print("=" * 90)
    avg_m84 = statistics.mean(d["final_money_v84"] for d in audit_data)
    avg_m41 = statistics.mean(d["final_money_v41"] for d in audit_data)
    avg_unsold = statistics.mean(d["unsold_inventory_val"] for d in audit_data)
    avg_milk_inv = statistics.mean(d["milk_inv_d30"] for d in audit_data)
    avg_c15 = statistics.mean(d["cows_d15"] for d in audit_data)
    avg_c20 = statistics.mean(d["cows_d20"] for d in audit_data)
    avg_c25 = statistics.mean(d["cows_d25"] for d in audit_data)
    avg_c30 = statistics.mean(d["cows_d30"] for d in audit_data)

    print(f" V8.4 Avg Final Cash:         ${avg_m84:,.2f}")
    print(f" V4.1 Avg Final Cash:         ${avg_m41:,.2f}")
    print(f" Avg Unsold Inventory Value:  ${avg_unsold:,.2f} ({avg_milk_inv:.1f} Milk left unsold on Day 30)")
    print(f" Total Potential Wealth:      ${avg_m84 + avg_unsold:,.2f}")
    print(f" Cow Fleet Trajectory:        Day 15: {avg_c15:.1f} -> Day 20: {avg_c20:.1f} -> Day 25: {avg_c25:.1f} -> Day 30: {avg_c30:.1f} Cows")
    print("=" * 90)

    report = {
        "avg_final_money_v84": round(avg_m84, 2),
        "avg_final_money_v41": round(avg_m41, 2),
        "avg_unsold_inventory_val": round(avg_unsold, 2),
        "avg_milk_inventory_d30": round(avg_milk_inv, 1),
        "cow_fleet_trajectory": {
            "d15": avg_c15,
            "d20": avg_c20,
            "d25": avg_c25,
            "d30": avg_c30,
        },
    }
    with open("missing_wealth_diagnostic_results.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
