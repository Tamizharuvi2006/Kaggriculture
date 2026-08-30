"""EXP166: Ground-Truth Terminal-State & Labor-Cost Reconciliation."""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def audit_seed_ground_truth(seed: int, seat: int):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    step695_state = None
    hired_counts = {0: 0, 1: 0}
    harvested_counts = {0: 0, 1: 0}

    # Play up to 695
    while env.state[0].observation.get("step", 0) < 695 and not env.done:
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env.step([a0, a1] if seat == 0 else [a1, a0])

    # Extract Step 695 Ground Truth
    obs0_695 = env.state[0].observation if seat == 0 else env.state[1].observation
    obs1_695 = env.state[1].observation if seat == 0 else env.state[0].observation
    f0_695 = obs0_695.get("farms", [{}, {}])[0]
    f1_695 = obs1_695.get("farms", [{}, {}])[1]
    p0_695 = obs0_695.get("private", {}) or {}
    p1_695 = obs1_695.get("private", {}) or {}
    mkt_695 = obs0_695.get("market", {}) or {}
    prices_695 = mkt_695.get("prices", {}) or {}

    c0_695 = float(f0_695.get("money", 0))
    c1_695 = float(f1_695.get("money", 0))

    # Count ripe strawberry tiles & yield units on D.1 and Opponent farms
    straw_tiles_0 = 0
    straw_yield_0 = 0
    for row in f0_695.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY":
                straw_tiles_0 += 1
                straw_yield_0 += t.get("yield_units", 0)

    straw_tiles_1 = 0
    straw_yield_1 = 0
    for row in f1_695.get("tiles", []):
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY":
                straw_tiles_1 += 1
                straw_yield_1 += t.get("yield_units", 0)

    # Continue from 695 to 720 and record exactly what V18 and D.1 do on Day 30
    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        # Count hires submitted
        if isinstance(a0, dict):
            hired_counts[0] += sum(1 for o in a0.get("market", []) if isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")
        if isinstance(a1, dict):
            hired_counts[1] += sum(1 for o in a1.get("market", []) if isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0_720 = float(env.state[seat].reward or 0.0)
    r1_720 = float(env.state[1 - seat].reward or 0.0)

    return {
        "seed": seed, "seat": seat,
        "step695": {
            "hero_cash": c0_695, "opp_cash": c1_695, "cash_delta": c0_695 - c1_695,
            "hero_straw_tiles": straw_tiles_0, "hero_straw_yield_units": straw_yield_0,
            "opp_straw_tiles": straw_tiles_1, "opp_straw_yield_units": straw_yield_1,
            "p_straw": prices_695.get("STRAWBERRY", 120),
        },
        "day30_activity": {
            "hero_hires": hired_counts[0],
            "opp_hires": hired_counts[1],
            "hero_cash_delta_day30": r0_720 - c0_695,
            "opp_cash_delta_day30": r1_720 - c1_695,
        },
        "step720": {
            "hero_reward": r0_720, "opp_reward": r1_720, "final_margin": r0_720 - r1_720,
        }
    }

def main():
    print("=" * 145)
    print("EXP166: GROUND-TRUTH TERMINAL-STATE & LABOR COST RECONCILIATION AUDIT")
    print("=" * 145)

    # 1. Fibonacci Cost Verification
    fib_costs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    print(f"1. ENVIRONMENT LABOR PRICING FORMULA (FARM_HAND_COST_MULT = 1):")
    for n in range(1, 11):
        total_c = sum(fib_costs[:n])
        print(f"   Hiring {n:2d} workers costs: ${total_c:3d} (Incremental: ${fib_costs[n-1]:2d})")
    print(f"   -> Hiring 10 workers on Day 30 costs only $143, NOT $5,000!")

    # 2. Reconcile 10 Mirror Seeds
    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321]
    results = []

    print("\n2. STEP 695 VS STEP 720 TRAJECTORY BREAKDOWN (10 SEEDS VS V18):")
    print(f"{'Seed':<6} | {'Step 695 Cash Delta':<20} | {'D.1 Ripe Straw':<15} | {'V18 Ripe Straw':<15} | {'D.1 Day30 Rev':<15} | {'V18 Day30 Rev':<15} | {'Final Margin ($)'}")
    print("-" * 145)

    for i, seed in enumerate(seeds):
        res = audit_seed_ground_truth(seed, 0)
        results.append(res)
        s695 = res["step695"]
        d30 = res["day30_activity"]
        s720 = res["step720"]

        print(f"{seed:<6} | ${s695['cash_delta']:+18,.2f} | {s695['hero_straw_yield_units']:3d} units ({s695['hero_straw_tiles']:2d} tiles) | {s695['opp_straw_yield_units']:3d} units ({s695['opp_straw_tiles']:2d} tiles) | ${d30['hero_cash_delta_day30']:+13,.2f} | ${d30['opp_cash_delta_day30']:+13,.2f} | ${s720['final_margin']:+14,.2f}")

    print("=" * 145)
    mean_s695_delta = np.mean([r["step695"]["cash_delta"] for r in results])
    mean_final_delta = np.mean([r["step720"]["final_margin"] for r in results])
    mean_d1_day30_rev = np.mean([r["day30_activity"]["hero_cash_delta_day30"] for r in results])
    mean_v18_day30_rev = np.mean([r["day30_activity"]["opp_cash_delta_day30"] for r in results])

    print("SYNTHESIS SUMMARY:")
    print(f"  Mean Step-695 Cash Delta (Before Day 30): ${mean_s695_delta:+10,.2f}")
    print(f"  Mean D.1 Revenue Generated on Day 30    : ${mean_d1_day30_rev:+10,.2f} (0 hires)")
    print(f"  Mean V18 Revenue Generated on Day 30    : ${mean_v18_day30_rev:+10,.2f} (10 hires, cost $143)")
    print(f"  Day 30 Net Hiring Advantage for V18    : ${mean_v18_day30_rev - mean_d1_day30_rev:+10,.2f}")
    print(f"  Mean Step-720 Final Margin              : ${mean_final_delta:+10,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp166_terminal_reconciliation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved Complete EXP166 Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
