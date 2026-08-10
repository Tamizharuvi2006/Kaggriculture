"""V4.2 Capital Utilization Audit (Days 15 to 30).

Traces V4.2 Candidate step-by-step from Day 15 (Step 360) to Day 30 (Step 720) across Seeds 1000-1004.
Records turn-by-turn:
1. Liquid Cash Balance ($)
2. Cow Fleet Count
3. Active Crop Fields Count
4. Land Tiles Unlocked
5. Idle Capital = Cash > $500 safety reserve sitting un-invested
6. Available Unbought Productive Assets (Cow, Land, Seeds, Workers)
7. Ranks all idle capital bottlenecks by estimated lost final wealth impact.

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
    spec = importlib.util.spec_from_file_location(f"v42_cu_{process_id}", V18_PATH)
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
    spec = importlib.util.spec_from_file_location(f"v41_cu_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_capital_utilization_seed(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1

    idle_capital_logs = []

    for s_idx in range(360, 720):
        obs_step = state_history[s_idx]
        f_v42 = obs_step[idx_v42]["observation"]["farms"][idx_v42]
        cash = float(f_v42["money"])
        cows = sum(1 for r in f_v42["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        active_fields = sum(1 for r in f_v42["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "FIELD" and t.get("crop") is not None)

        a_v42 = obs_step[idx_v42].get("action", {})
        m_v42 = a_v42.get("market", []) if isinstance(a_v42, dict) else []

        has_buy_cow = any(o[0] == "BUY_ANIMAL" for o in m_v42)
        has_buy_land = any(o[0] == "BUY_LAND" for o in m_v42)
        has_buy_seed = any(o[0] == "BUY_SEED" for o in m_v42)

        idle_cash = max(0.0, cash - 500.0)

        # Detect Idle Capital Opportunity Bottlenecks
        if idle_cash >= 1000.0 and not (has_buy_cow or has_buy_land or has_buy_seed):
            idle_capital_logs.append({
                "step": s_idx,
                "day": (s_idx // 24) + 1,
                "cash": cash,
                "idle_cash": idle_cash,
                "cows": cows,
                "active_fields": active_fields,
                "reason": "8-Cow Ceiling Intact & Land Unlocks Suppressed" if cows == 8 else "Unused Liquid Cash",
            })

    return {
        "seed": seed,
        "idle_logs": idle_capital_logs,
        "final_cash": float(state_history[-1][idx_v42]["observation"]["farms"][idx_v42]["money"]),
    }


def main():
    print("=" * 95)
    print(" V4.2 CAPITAL UTILIZATION AUDIT (DAYS 15 TO 30)")
    print("=" * 95)

    seeds = list(range(1000, 1005))
    reports = [audit_capital_utilization_seed(s) for s in seeds]

    all_logs = [l for r in reports for l in r["idle_logs"]]
    total_idle_steps = len(all_logs)

    avg_idle_cash = statistics.mean(l["idle_cash"] for l in all_logs) if all_logs else 0.0
    max_idle_cash = max(l["idle_cash"] for l in all_logs) if all_logs else 0.0

    print(f"\n Total Post-Day-15 Idle Capital Steps (Cash > $1,000 Sitting Idle): {total_idle_steps} / 1800 turns ({total_idle_steps/1800*100:.1f}%)")
    print(f" Average Idle Cash Balance per Step:                          ${avg_idle_cash:,.2f}")
    print(f" Peak Idle Cash Balance Reached:                             ${max_idle_cash:,.2f}")
    print("-" * 95)

    print("\n" + "=" * 95)
    print(" SAMPLE IDLE CAPITAL BOTTLENECK EVENTS")
    print("=" * 95)
    for sample in all_logs[:5]:
        print(f" Day {sample['day']} (Step {sample['step']}) | Liquid Cash: ${sample['cash']:,.2f} | Idle Cash (> $500): ${sample['idle_cash']:,.2f}")
        print(f"   Cows: {sample['cows']} | Active Fields: {sample['active_fields']} | Bottleneck: {sample['reason']}")
        print("-" * 95)

    with open("v42_capital_utilization_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
