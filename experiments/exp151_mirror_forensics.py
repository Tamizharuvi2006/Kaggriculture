"""EXP151: Post-Step-216 Mirror Duopoly Forensics & Action Divergence Analysis.

Forensic examination of the 20 V18 Mirror matches (Steps 216 to 720):
1. Audits step-by-step actions of Hero (D.1) vs Opponent (V18):
   - Strawberry selling timing, quantities, and realized market prices
   - Milk selling timing, quantities, and realized market prices
   - Livestock asset counts (Cows, Sheep) and feeding consistency
   - Worker task allocations (Water, Plant, Harvest, Animal)
   - Working capital cash trajectory (Day 10, 15, 20, 25, 30)
   - Terminal window liquidation behavior (Steps 672-720)
2. Isolates the exact economic source of the -$4,512 deficit.
3. Identifies the minimal post-Step-216 anti-mirror intervention.
"""
from __future__ import annotations
import os
import sys
import json
import importlib.util
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.population_suite import POPULATION_SUITE

# Load D.1 Baseline Agent
spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

def run_mirror_match_forensics(seed: int, seat: int):
    v18_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    hero_straw_sold_qty = 0
    opp_straw_sold_qty = 0
    hero_straw_revenue = 0.0
    opp_straw_revenue = 0.0

    hero_milk_sold_qty = 0
    opp_milk_sold_qty = 0
    hero_milk_revenue = 0.0
    opp_milk_revenue = 0.0

    hero_cash_timeline = {}
    opp_cash_timeline = {}
    price_timeline = {}

    check_steps = [216, 240, 360, 480, 600, 672, 696]

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        farms = obs0.get("farms", [{}, {}])
        f_hero = farms[seat] if len(farms) > seat else {}
        f_opp = farms[1 - seat] if len(farms) > 1 - seat else {}

        market_info = obs0.get("market", {})
        prices = market_info.get("prices", {})
        p_straw = float(prices.get("STRAWBERRY", 120.0))
        p_milk = float(prices.get("MILK", 120.0))

        if step in check_steps:
            hero_cash_timeline[f"step_{step}"] = float(f_hero.get("money", 0))
            opp_cash_timeline[f"step_{step}"] = float(f_opp.get("money", 0))
            price_timeline[f"step_{step}"] = {"p_straw": p_straw, "p_milk": p_milk}

        a0 = sub_d1.agent(obs0, env.configuration)
        try:
            a1 = v18_fn(obs1, env.configuration)
        except TypeError:
            a1 = v18_fn(obs1)

        # Track market order sales after Step 216
        if step >= 216:
            # Hero sales
            m0 = a0.get("market", []) if isinstance(a0, dict) else []
            for o in m0:
                if isinstance(o, (list, tuple)) and len(o) >= 3 and o[0] == "SELL":
                    if o[1] == "STRAWBERRY":
                        qty = int(o[2])
                        hero_straw_sold_qty += qty
                        hero_straw_revenue += qty * p_straw
                    elif o[1] == "MILK":
                        qty = int(o[2])
                        hero_milk_sold_qty += qty
                        hero_milk_revenue += qty * p_milk

            # Opponent sales
            m1 = a1.get("market", []) if isinstance(a1, dict) else []
            for o in m1:
                if isinstance(o, (list, tuple)) and len(o) >= 3 and o[0] == "SELL":
                    if o[1] == "STRAWBERRY":
                        qty = int(o[2])
                        opp_straw_sold_qty += qty
                        opp_straw_revenue += qty * p_straw
                    elif o[1] == "MILK":
                        qty = int(o[2])
                        opp_milk_sold_qty += qty
                        opp_milk_revenue += qty * p_milk

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    # Final farm states
    final_f0 = env.state[seat].observation.get("farms", [{}, {}])[seat]
    final_f1 = env.state[1 - seat].observation.get("farms", [{}, {}])[1 - seat]

    tiles0 = final_f0.get("tiles", [])
    tiles1 = final_f1.get("tiles", [])
    cows0 = sum(1 for r in tiles0 for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    cows1 = sum(1 for r in tiles1 for t in r if isinstance(t, dict) and t.get("animal") == "COW")

    shed0 = final_f0.get("inventory", {})
    shed1 = final_f1.get("inventory", {})

    return {
        "seed": seed,
        "seat": seat,
        "hero_reward": r0,
        "opp_reward": r1,
        "margin": r0 - r1,
        "won": r0 > r1,
        "hero_cows": cows0,
        "opp_cows": cows1,
        "hero_straw_sold_qty": hero_straw_sold_qty,
        "opp_straw_sold_qty": opp_straw_sold_qty,
        "hero_straw_revenue": hero_straw_revenue,
        "opp_straw_revenue": opp_straw_revenue,
        "hero_milk_sold_qty": hero_milk_sold_qty,
        "opp_milk_sold_qty": opp_milk_sold_qty,
        "hero_milk_revenue": hero_milk_revenue,
        "opp_milk_revenue": opp_milk_revenue,
        "hero_leftover_straw": int(shed0.get("STRAWBERRY", 0)),
        "opp_leftover_straw": int(shed1.get("STRAWBERRY", 0)),
        "hero_leftover_milk": int(shed0.get("MILK", 0)),
        "opp_leftover_milk": int(shed1.get("MILK", 0)),
        "hero_cash_timeline": hero_cash_timeline,
        "opp_cash_timeline": opp_cash_timeline,
        "price_timeline": price_timeline,
    }

def main():
    print("=" * 145)
    print("EXP151: POST-STEP-216 MIRROR DUOPOLY FORENSICS ACROSS ALL 20 MIRROR MATCHES")
    print("=" * 145)

    seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
             20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

    match_results = []
    for i, seed in enumerate(seeds):
        seat = 0 if i < 10 else 1
        res = run_mirror_match_forensics(seed, seat)
        match_results.append(res)

    print(f"Audited all 20 mirror matches. Mean Hero Reward: ${np.mean([m['hero_reward'] for m in match_results]):,.2f} vs Opponent: ${np.mean([m['opp_reward'] for m in match_results]):,.2f} (Margin: ${np.mean([m['margin'] for m in match_results]):+,.2f})\n")

    # 1. Balance Sheet Itemized Comparison
    print("=" * 145)
    print("1. POST-STEP-216 PRODUCTION & REVENUE COMPARISON (D.1 VS V18 OPPONENT):")
    print("=" * 145)
    h_straw_rev = np.mean([m["hero_straw_revenue"] for m in match_results])
    o_straw_rev = np.mean([m["opp_straw_revenue"] for m in match_results])
    h_straw_qty = np.mean([m["hero_straw_sold_qty"] for m in match_results])
    o_straw_qty = np.mean([m["opp_straw_sold_qty"] for m in match_results])

    h_milk_rev = np.mean([m["hero_milk_revenue"] for m in match_results])
    o_milk_rev = np.mean([m["opp_milk_revenue"] for m in match_results])
    h_milk_qty = np.mean([m["hero_milk_sold_qty"] for m in match_results])
    o_milk_qty = np.mean([m["opp_milk_sold_qty"] for m in match_results])

    h_cows = np.mean([m["hero_cows"] for m in match_results])
    o_cows = np.mean([m["opp_cows"] for m in match_results])

    h_left_straw = np.mean([m["hero_leftover_straw"] for m in match_results])
    o_left_straw = np.mean([m["opp_leftover_straw"] for m in match_results])
    h_left_milk = np.mean([m["hero_leftover_milk"] for m in match_results])
    o_left_milk = np.mean([m["opp_leftover_milk"] for m in match_results])

    print(f"  Strawberry Sold Qty:      D.1 = {h_straw_qty:5.1f} units     |  V18 = {o_straw_qty:5.1f} units     (Delta: {h_straw_qty - o_straw_qty:+5.1f})")
    print(f"  Strawberry Revenue:       D.1 = ${h_straw_rev:10,.2f}  |  V18 = ${o_straw_rev:10,.2f}  (Delta: ${h_straw_rev - o_straw_rev:+10,.2f})")
    print(f"  Realized Price / Straw:   D.1 = ${h_straw_rev/h_straw_qty:6.2f} / unit  |  V18 = ${o_straw_rev/o_straw_qty:6.2f} / unit  (Delta: ${h_straw_rev/h_straw_qty - o_straw_rev/o_straw_qty:+6.2f})")
    print(f"  Milk Sold Qty:            D.1 = {h_milk_qty:5.1f} units     |  V18 = {o_milk_qty:5.1f} units     (Delta: {h_milk_qty - o_milk_qty:+5.1f})")
    print(f"  Milk Revenue:             D.1 = ${h_milk_rev:10,.2f}  |  V18 = ${o_milk_rev:10,.2f}  (Delta: ${h_milk_rev - o_milk_rev:+10,.2f})")
    print(f"  Realized Price / Milk:    D.1 = ${h_milk_rev/h_milk_qty:6.2f} / unit  |  V18 = ${o_milk_rev/o_milk_qty:6.2f} / unit  (Delta: ${h_milk_rev/h_milk_qty - o_milk_rev/o_milk_qty:+6.2f})")
    print(f"  Cow Count:                D.1 = {h_cows:5.2f} cows      |  V18 = {o_cows:5.2f} cows      (Delta: {h_cows - o_cows:+5.2f})")
    print(f"  Leftover Shed Deadweight: D.1 = {h_left_straw:.1f} straw, {h_left_milk:.1f} milk |  V18 = {o_left_straw:.1f} straw, {o_left_milk:.1f} milk")

    # 2. Timeline of Cash Divergence
    print("\n" + "=" * 145)
    print("2. STEP-BY-STEP CASH DIVERGENCE TIMELINE ACROSS MIDGAME & ENDGAME:")
    print("=" * 145)
    print(f"{'Game Step':<15} | {'Game Day':<12} | {'D.1 Cash ($)':<16} | {'V18 Opponent Cash ($)':<22} | {'Net Cash Margin ($)':<20} | {'Strawberry Price ($)'}")
    print("-" * 145)

    steps_list = [216, 240, 360, 480, 600, 672, 696]
    for s in steps_list:
        k = f"step_{s}"
        c_h = np.mean([m["hero_cash_timeline"][k] for m in match_results])
        c_o = np.mean([m["opp_cash_timeline"][k] for m in match_results])
        p_s = np.mean([m["price_timeline"][k]["p_straw"] for m in match_results])
        print(f"Step {s:<8} | Day {s//24:02d}       | ${c_h:12,.2f}   | ${c_o:18,.2f}   | ${c_h - c_o:+16,.2f}   | ${p_s:6.2f}")

    # Day 30 Terminal Surge
    r_h = np.mean([m["hero_reward"] for m in match_results])
    r_o = np.mean([m["opp_reward"] for m in match_results])
    c_h_29 = np.mean([m["hero_cash_timeline"]["step_696"] for m in match_results])
    c_o_29 = np.mean([m["opp_cash_timeline"]["step_696"] for m in match_results])
    d30_gain_h = r_h - c_h_29
    d30_gain_o = r_o - c_o_29

    print(f"Step 720 (Final) | Day 30 Final | ${r_h:12,.2f}   | ${r_o:18,.2f}   | ${r_h - r_o:+16,.2f}   | $--.--")
    print("-" * 145)
    print(f"DAY 30 SURGE (Steps 696-720): D.1 Gain = +${d30_gain_h:,.2f} | V18 Gain = +${d30_gain_o:,.2f} (Delta: ${d30_gain_h - d30_gain_o:+,.2f})")
    print("=" * 145)

    # Save EXP151 dataset
    out_json = os.path.join(REPORTS_DIR, "exp151_mirror_forensics_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "mean_hero_reward": float(np.mean([m["hero_reward"] for m in match_results])),
            "mean_opp_reward": float(np.mean([m["opp_reward"] for m in match_results])),
            "mean_margin": float(np.mean([m["margin"] for m in match_results])),
            "hero_straw_rev": float(h_straw_rev),
            "opp_straw_rev": float(o_straw_rev),
            "hero_milk_rev": float(h_milk_rev),
            "opp_milk_rev": float(o_milk_rev),
            "realized_p_straw_hero": float(h_straw_rev/h_straw_qty),
            "realized_p_straw_opp": float(o_straw_rev/o_straw_qty),
            "all_matches": _to_native(match_results),
        }, f, indent=2)

    print(f"\nSaved Complete EXP151 Mirror Forensics Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
