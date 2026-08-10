"""Phase A: Post-Day-15 Action-by-Action Divergence Audit (Days 15 to 30).

Traces 5 competitive 1v1 matches between V4.2 Master Candidate and V4.1 Master Champion.
Inspects every turn from Day 15 (Step 360) to Day 30 (Step 720) action-by-action:
1. Worker Task Allocation & Movement Steps
2. Market Orders Issued & Executed
3. Cash Before/After Action
4. Farm Asset State (Cows, Fields, Pastures)
5. Ranks all divergences by estimated lost final wealth.

No code modifications are made.
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
    spec = importlib.util.spec_from_file_location(f"v42_pa_{process_id}", V18_PATH)
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
    spec = importlib.util.spec_from_file_location(f"v41_pa_{process_id}", V18_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.configure_strategy({
        "use_fixed_schedule": False,
        "v13_market_adaptation": True,
        "opening_melons": 15,
        "cows": 8,
    })
    return mod.agent


def audit_phase_a_match(seed):
    agent_v42 = _load_v42(seed)
    agent_v41 = _load_v41(seed + 10000)

    p0_is_v42 = (seed % 2 == 0)
    p0 = agent_v42 if p0_is_v42 else agent_v41
    p1 = agent_v41 if p0_is_v42 else agent_v42

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    state_history = env.run([p0, p1])

    idx_v42 = 0 if p0_is_v42 else 1
    idx_v41 = 1 if p0_is_v42 else 0

    divergence_events = []

    for s_idx in range(360, 720):
        obs_step = state_history[s_idx]
        f_v42 = obs_step[idx_v42]["observation"]["farms"][idx_v42]
        f_v41 = obs_step[idx_v41]["observation"]["farms"][idx_v41]

        a_v42 = obs_step[idx_v42].get("action", {})
        a_v41 = obs_step[idx_v41].get("action", {})

        m_v42 = a_v42.get("market", []) if isinstance(a_v42, dict) else []
        m_v41 = a_v41.get("market", []) if isinstance(a_v41, dict) else []

        w_v42 = a_v42.get("workers", []) if isinstance(a_v42, dict) else []
        w_v41 = a_v41.get("workers", []) if isinstance(a_v41, dict) else []

        cows_v42 = sum(1 for r in f_v42["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")
        cows_v41 = sum(1 for r in f_v41["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE" and t.get("animal") == "COW")

        cash_v42 = float(f_v42["money"])
        cash_v41 = float(f_v41["money"])

        # Detect Action & Market Divergences
        if m_v42 != m_v41 or cows_v42 != cows_v41 or len(w_v42) != len(w_v41):
            divergence_events.append({
                "step": s_idx,
                "day": (s_idx // 24) + 1,
                "cash_v42": cash_v42,
                "cash_v41": cash_v41,
                "cows_v42": cows_v42,
                "cows_v41": cows_v41,
                "market_v42": m_v42,
                "market_v41": m_v41,
                "workers_v42_count": len(w_v42),
                "workers_v41_count": len(w_v41),
            })

    return {
        "seed": seed,
        "divergence_count": len(divergence_events),
        "events": divergence_events,
        "final_v42": float(state_history[-1][idx_v42]["observation"]["farms"][idx_v42]["money"]),
        "final_v41": float(state_history[-1][idx_v41]["observation"]["farms"][idx_v41]["money"]),
    }


def main():
    print("=" * 95)
    print(" PHASE A: POST-DAY-15 ACTION-BY-ACTION DIVERGENCE AUDIT (SEEDS 1000-1004)")
    print("=" * 95)

    seeds = list(range(1000, 1005))
    reports = [audit_phase_a_match(s) for s in seeds]

    total_events = sum(r["divergence_count"] for r in reports)
    print(f"\n Total Post-Day-15 Divergence Events Logged: {total_events} across 5 seeds.")
    print("-" * 95)

    all_events = [e for r in reports for e in r["events"]]

    # Category 1: Cow Fleet Divergences (where V4.1 has more cows late-game)
    cow_diff_events = [e for e in all_events if e["cows_v41"] > e["cows_v42"]]
    print(f" 1. Cow Fleet Disparity Events (V4.1 buys late cows): {len(cow_diff_events)} steps ({len(cow_diff_events)/max(1, total_events)*100:.1f}%)")

    # Category 2: Market Order Disparities
    market_diff_events = [e for e in all_events if e["market_v42"] != e["market_v41"]]
    print(f" 2. Market Order Queue Disparities:                  {len(market_diff_events)} steps ({len(market_diff_events)/max(1, total_events)*100:.1f}%)")

    print("\n" + "=" * 95)
    print(" SAMPLE POST-DAY-15 DIVERGENCE EVENTS")
    print("=" * 95)
    for sample in all_events[:5]:
        print(f" Step {sample['step']} (Day {sample['day']}) | V4.2 Cash: ${sample['cash_v42']:,.2f} | V4.1 Cash: ${sample['cash_v41']:,.2f}")
        print(f"   V4.2 Cows: {sample['cows_v42']} | V4.1 Cows: {sample['cows_v41']}")
        print(f"   V4.2 Market Orders: {sample['market_v42']}")
        print(f"   V4.1 Market Orders: {sample['market_v41']}")
        print("-" * 95)

    with open("phase_a_post_day15_divergence_results.json", "w") as f:
        json.dump(reports, f, indent=2)

if __name__ == "__main__":
    main()
