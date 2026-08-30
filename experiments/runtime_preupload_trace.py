"""EXP170 Final Pre-Upload Runtime Trace & Step-Level Engine Verification."""
from __future__ import annotations
import os
import sys
import json
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.live_calibrated_suite import LIVE_CALIBRATED_DISTRIBUTION

# Import Control D.1
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

# Import Candidate Adaptive Terminal
spec_cand = importlib.util.spec_from_file_location("sub_cand", os.path.join(BASE_DIR, "candidate_adaptive_terminal.py"))
sub_cand = importlib.util.module_from_spec(spec_cand)
spec_cand.loader.exec_module(sub_cand)

FIB_CUMULATIVE = [0, 1, 2, 4, 7, 12, 20, 33, 54, 88, 143]

def run_trace(seed: int, opp_key: str, scenario_name: str):
    print("\n" + "=" * 120)
    print(f"SCENARIO: {scenario_name} (Seed: {seed}, Opponent: {opp_key})")
    print("=" * 120)

    opp_fn = LIVE_CALIBRATED_DISTRIBUTION[opp_key]["agent"]

    # 1. Parity Check: Play Steps 0-695
    env_cand = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_cand.reset()

    parity_diffs = 0
    while env_cand.state[0].observation.get("step", 0) <= 695:
        obs0 = env_cand.state[0].observation
        obs1 = env_cand.state[1].observation

        act_d1 = sub_d1.agent(obs0, env_cand.configuration)
        act_cand = sub_cand.agent(obs0, env_cand.configuration)

        if act_d1 != act_cand:
            parity_diffs += 1
            print(f"  ❌ Divergence at Step {obs0.get('step')}: D1={act_d1} vs CAND={act_cand}")

        try: act1 = opp_fn(obs1, env_cand.configuration)
        except TypeError: act1 = opp_fn(obs1)
        env_cand.step([act_cand, act1])

    print(f"1. Steps 0-695 Action Parity vs D.1 Baseline: {parity_diffs} differences ({'PASS ✅' if parity_diffs == 0 else 'FAIL ❌'})")

    # Step 695 state audit
    obs_695 = env_cand.state[0].observation
    f0_695 = obs_695.get("farms", [{}, {}])[0]
    cash_695 = float(f0_695.get("money", 0))

    # Evaluate observable backlog at Step 696
    obs_696 = env_cand.state[0].observation
    f0_696 = obs_696.get("farms", [{}, {}])[0]
    cash_696 = float(f0_696.get("money", 0))
    prices_696 = (obs_696.get("market") or {}).get("prices") or {}
    p_straw = float(prices_696.get("STRAWBERRY", 120.0) or 120.0)
    p_milk = float(prices_696.get("MILK", 193.0) or 193.0)
    p_wool = float(prices_696.get("WOOL", 150.0) or 150.0)

    ripe_plant_tiles = 0
    ripe_animal_tiles = 0
    pred_recoverable_value = 0.0

    for r in f0_696.get("tiles", []):
        for t in r:
            if isinstance(t, dict):
                y = t.get("yield_units", 0)
                if t.get("kind") == "PLANT" and y > 0:
                    ripe_plant_tiles += 1
                    crop = t.get("crop")
                    p = p_straw if crop == "STRAWBERRY" else (35.0 if crop == "CARROT" else 20.0)
                    pred_recoverable_value += y * p
                elif "animal" in t and y > 0:
                    ripe_animal_tiles += 1
                    a = t.get("animal")
                    p = p_milk if a == "COW" else p_wool
                    pred_recoverable_value += y * p

    total_ripe_tiles = ripe_plant_tiles + ripe_animal_tiles
    print(f"2. Step 696 Observable Field State:")
    print(f"   - Ripe Plant Tiles : {ripe_plant_tiles}")
    print(f"   - Ripe Animal Tiles: {ripe_animal_tiles}")
    print(f"   - Total Ripe Tiles : {total_ripe_tiles}")
    print(f"   - Predicted Value  : ${pred_recoverable_value:,.2f}")

    # Candidate decision at Step 696
    act_cand_696 = sub_cand.agent(obs_696, env_cand.configuration)
    hire_orders = [o for o in act_cand_696.get("market", []) if isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE"]
    n_hired = len(hire_orders)

    try: act1_696 = opp_fn(env_cand.state[1].observation, env_cand.configuration)
    except TypeError: act1_696 = opp_fn(env_cand.state[1].observation)
    env_cand.step([act_cand_696, act1_696])

    # Step 697 engine inspection
    obs_697 = env_cand.state[0].observation
    f0_697 = obs_697.get("farms", [{}, {}])[0]
    cash_697 = float(f0_697.get("money", 0))
    hands_697 = f0_697.get("hands", [])
    num_hands = len(hands_697)
    actual_cost = cash_696 - cash_697

    print(f"3. Step 696 Execution & Labor Deductions:")
    print(f"   - HIRE Orders Submitted: {n_hired}")
    print(f"   - Expected Fibonacci Cost: ${FIB_CUMULATIVE[n_hired]:.2f}")
    print(f"   - Actual Cash Deducted   : ${actual_cost:.2f} ({'PASS ✅' if actual_cost == FIB_CUMULATIVE[n_hired] else 'FAIL ❌'})")
    print(f"   - Workers Spawned in Game: {num_hands} ({'PASS ✅' if num_hands == n_hired else 'FAIL ❌'})")
    if num_hands > 0:
        print(f"   - Spawn Positions: Farmer at {f0_697.get('farmer')}, Hands at {[h[:2] if isinstance(h, list) else h for h in hands_697]}")

    # Trace Steps 697 to 719
    print(f"\n4. Tracing Steps 697-719 (Actions, Shed Inventory, & Sales Execution):")
    total_straw_sold = 0
    total_milk_sold = 0
    total_wool_sold = 0
    total_fert_sold = 0
    total_sales_revenue = 0.0

    step_traces = []
    while not env_cand.done:
        step = env_cand.state[0].observation.get("step", 0)
        o0 = env_cand.state[0].observation
        o1 = env_cand.state[1].observation
        c_before = float(o0.get("farms", [{}, {}])[0].get("money", 0))

        a0 = sub_cand.agent(o0, env_cand.configuration)
        try: a1 = opp_fn(o1, env_cand.configuration)
        except TypeError: a1 = opp_fn(o1)
        env_cand.step([a0, a1])

        c_after = float(env_cand.state[0].observation.get("farms", [{}, {}])[0].get("money", 0))
        sales_this_step = max(0.0, c_after - c_before)
        total_sales_revenue += sales_this_step

        m_orders = a0.get("market", [])
        for m in m_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 3 and m[0] == "SELL":
                item, qty = m[1], int(m[2])
                if item == "STRAWBERRY": total_straw_sold += qty
                elif item == "MILK": total_milk_sold += qty
                elif item == "WOOL": total_wool_sold += qty
                elif item == "FERTILIZER": total_fert_sold += qty

        if step in [697, 698, 700, 705, 710, 715, 719]:
            step_traces.append({
                "step": step,
                "farmer_act": a0.get("farmer"),
                "num_hand_acts": len(a0.get("hands", [])),
                "sample_hand_acts": a0.get("hands", [])[:3],
                "market_orders": m_orders,
                "sales_revenue": sales_this_step,
                "cash": c_after,
            })

    for st in step_traces:
        print(f"   Step {st['step']:3d}: Farmer={st['farmer_act']}, Hands={st['num_hand_acts']} acts {st['sample_hand_acts']}..., Market={st['market_orders']}, Sales=+${st['sales_revenue']:,.2f}, Bank=${st['cash']:,.2f}")

    final_cand_reward = float(env_cand.state[0].reward or 0)
    opp_reward = float(env_cand.state[1].reward or 0)
    net_sales_day29 = total_sales_revenue
    net_profit_day29 = net_sales_day29 - actual_cost

    print(f"\n5. Day 29 Production & Commodity Sales Summary:")
    print(f"   - Strawberries Sold : {total_straw_sold} units")
    print(f"   - Milk Sold         : {total_milk_sold} units")
    print(f"   - Wool Sold         : {total_wool_sold} units")
    print(f"   - Fertilizer Sold   : {total_fert_sold} units")
    print(f"   - Gross Sales Day 29: ${net_sales_day29:,.2f}")
    print(f"   - Labor Cost Paid   : ${actual_cost:.2f}")
    print(f"   - Net Day 29 Profit : ${net_profit_day29:,.2f}")
    print(f"   - Predicted Recoverable Value: ${pred_recoverable_value:,.2f} vs Actual Sales: ${net_sales_day29:,.2f}")

    # 6. Counterfactual D.1 Comparison
    env_d1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_d1.reset()
    while not env_d1.done:
        o0 = env_d1.state[0].observation
        o1 = env_d1.state[1].observation
        a0 = sub_d1.agent(o0, env_d1.configuration)
        try: a1 = opp_fn(o1, env_d1.configuration)
        except TypeError: a1 = opp_fn(o1)
        env_d1.step([a0, a1])

    final_d1_reward = float(env_d1.state[0].reward or 0)
    d1_won = final_d1_reward > float(env_d1.state[1].reward or 0)
    cand_won = final_cand_reward > opp_reward
    incremental_lead = final_cand_reward - final_d1_reward

    print(f"\n6. Counterfactual Match Outcome Comparison:")
    print(f"   - D.1 Baseline (N=0)   : ${final_d1_reward:,.2f} ({'WON 🏆' if d1_won else 'LOST 💀'})")
    print(f"   - Candidate N*         : ${final_cand_reward:,.2f} ({'WON 🏆' if cand_won else 'LOST 💀'}) vs Opponent: ${opp_reward:,.2f}")
    print(f"   - Incremental Terminal Gain: {incremental_lead:+,.2f}")

    pass_parity = (parity_diffs == 0)
    pass_cost = (actual_cost == FIB_CUMULATIVE[n_hired])
    pass_hands = (num_hands == n_hired)
    pass_outcome = (cand_won or (not d1_won and final_cand_reward >= final_d1_reward))

    overall_pass = pass_parity and pass_cost and pass_hands and pass_outcome
    print(f"\nSCENARIO VERDICT: {'PASS ✅' if overall_pass else 'FAIL ❌'}")
    return overall_pass

def main():
    print("=" * 120)
    print("EXP170: FINAL PRE-UPLOAD RUNTIME ENGINE TRACE & STEP-LEVEL AUDIT")
    print("=" * 120)

    # Test Case 1: Dense Strawberry Mirror (Seed 90012, Expected N*=10)
    pass1 = run_trace(seed=90012, opp_key="T1_v18_mirror", scenario_name="Dense Strawberry Duopoly Mirror (N*=10)")

    # Test Case 2: Another Dense Strawberry Mirror (Seed 1000, Expected N*=10)
    pass2 = run_trace(seed=1000, opp_key="T1_v18_mirror", scenario_name="Dense Strawberry Duopoly Mirror #2 (N*=10)")

    # Test Case 3: Sparse Cattle / Rusher Archetype (Seed 90001, Expected N*=0 or minor)
    pass3 = run_trace(seed=90001, opp_key="T1_carrot_rusher", scenario_name="Sparse Carrot Rusher Archetype (N*=0 Protection)")

    print("\n" + "=" * 120)
    print("FINAL PRE-UPLOAD RUNTIME AUDIT SUMMARY:")
    print(f"  - Dense Mirror State 1 (Seed 90012): {'PASS ✅' if pass1 else 'FAIL ❌'}")
    print(f"  - Dense Mirror State 2 (Seed 1000) : {'PASS ✅' if pass2 else 'FAIL ❌'}")
    print(f"  - Sparse Non-Mirror (Carrot Rusher): {'PASS ✅' if pass3 else 'FAIL ❌'}")
    print("=" * 120)

if __name__ == "__main__":
    main()
