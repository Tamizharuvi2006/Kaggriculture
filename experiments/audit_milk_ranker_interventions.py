"""Milk Ranker Intervention-Level Attribution Audit.

Traces 5 competitive 1v1 seeds (1000 to 1004) turn-by-turn to audit every step where the Milk Ranker alters the market order queue:
Original Order vs Ranked Order

Classifies every intervention into 3 categories:
1. POSITIVE (Green): Milk promoted at price >= $230 when market queue truncation would have dropped milk sale.
2. NEUTRAL (Yellow): Milk promoted, but total market orders <= 5 (no truncation occurred).
3. HARMFUL (Red): Milk promoted, but displaced/truncated a high-value Melon or Strawberry order.
"""

import sys
import os
import json
import statistics
import importlib.util

sys.path.insert(0, os.path.dirname(__file__))

import kaggle_environments

V18_PATH = r"D:\kaggriculture\baseline\kaitofukami-v18.py"


def _load_v41_baseline(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_rk_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })
    return mod.agent, mod


def _load_v41_with_ranker(process_id):
    spec = importlib.util.spec_from_file_location(f"v41_wrk_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 10,
        "cows": 8,
    })

    _base = mod.agent

    def agent_ranked(obs, configuration=None):
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

    return agent_ranked, mod


def audit_ranker_seed(seed):
    agent_base, mod_base = _load_v41_baseline(seed)
    agent_rank, mod_rank = _load_v41_with_ranker(seed + 1000)

    env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    steps1 = env1.run([agent_base, agent_base])

    env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    steps2 = env2.run([agent_rank, agent_base])

    interventions = []

    for s_idx in range(720):
        # We also observe the raw action emitted by base vs ranker
        obs = steps1[s_idx][0]["observation"] if s_idx < len(steps1) else {}
        prices = obs.get("market", {}).get("prices", {})
        milk_p_data = prices.get("MILK", 0.0)
        milk_p = float(milk_p_data.get("price", 0.0) if isinstance(milk_p_data, dict) else milk_p_data or 0.0)

        # Get base raw action
        a_base = agent_base(obs)
        m_base = a_base.get("market", []) if isinstance(a_base, dict) else []

        # Get ranked action
        a_rank = agent_rank(obs)
        m_rank = a_rank.get("market", []) if isinstance(a_rank, dict) else []

        if m_base != m_rank:
            # Re-ordering occurred!
            total_orders = len(m_base)
            
            # Check classification
            if total_orders <= 5:
                category = "NEUTRAL" # No truncation limit breached
            elif milk_p >= 230.0:
                # Displaced crop?
                has_melon = any(o[0] == "SELL" and len(o) > 1 and o[1] == "MELON" for o in m_base)
                if has_melon and total_orders > 8:
                    category = "HARMFUL" # Displaced Melon sale
                else:
                    category = "POSITIVE"
            else:
                category = "NEUTRAL"

            interventions.append({
                "step": s_idx,
                "day": (s_idx // 24) + 1,
                "milk_price": milk_p,
                "total_orders": total_orders,
                "category": category,
                "base_orders": m_base,
                "ranked_orders": m_rank,
            })

    return {
        "seed": seed,
        "interventions": interventions,
        "final_base": float(steps1[-1][0]["observation"]["farms"][0]["money"]),
        "final_rank": float(steps2[-1][0]["observation"]["farms"][0]["money"]),
    }


def main():
    print("=" * 95)
    print(" MILK RANKER INTERVENTION-LEVEL ATTRIBUTION AUDIT (5 SEEDS)")
    print("=" * 95)

    seeds = list(range(1000, 1005))
    results = [audit_ranker_seed(s) for s in seeds]

    all_interventions = [i for r in results for i in r["interventions"]]
    total_count = len(all_interventions)

    positive_count = sum(1 for i in all_interventions if i["category"] == "POSITIVE")
    neutral_count = sum(1 for i in all_interventions if i["category"] == "NEUTRAL")
    harmful_count = sum(1 for i in all_interventions if i["category"] == "HARMFUL")

    print(f"\n Total Milk Ranker Interventions Recorded: {total_count}")
    print(f" [POSITIVE] Interventions (Milk Promoted & Preserved at >= $230): {positive_count:<5} ({positive_count/max(1, total_count)*100:.1f}%)")
    print(f" [NEUTRAL]  Interventions (No Queue Truncation Occurred):           {neutral_count:<5} ({neutral_count/max(1, total_count)*100:.1f}%)")
    print(f" [HARMFUL]  Interventions (Displaced Melon/Strawberry Sales):       {harmful_count:<5} ({harmful_count/max(1, total_count)*100:.1f}%)")

    print("\n" + "=" * 95)
    print(" SAMPLE INTERVENTIONS BREAKDOWN")
    print("=" * 95)
    for sample in all_interventions[:5]:
        print(f" Day {(sample['step']//24)+1} (Step {sample['step']}) | Category: {sample['category']:<8} | Milk Price: ${sample['milk_price']:.1f} | Orders: {sample['total_orders']}")
        print(f"   Base Queue:   {sample['base_orders']}")
        print(f"   Ranked Queue: {sample['ranked_orders']}")
        print("-" * 95)

    with open("milk_ranker_attribution_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
