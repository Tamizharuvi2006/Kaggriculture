"""EXP163: Real-Meta Forensic Divergence Miner across Strawberry Duopolies."""
from __future__ import annotations
import os
import sys
import json
import time
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

MIRROR_SEEDS = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
                20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

def mine_mirror_match_telemetry(seed: int, seat: int):
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    step_log = []
    
    first_divergence = None
    divergence_details = None

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        f0 = obs0.get("farms", [{}, {}])[0]
        f1 = obs1.get("farms", [{}, {}])[0]
        mkt = obs0.get("market", {}) or {}
        prices = mkt.get("prices", {}) or {}

        c0 = float(f0.get("money", 0) or 0)
        c1 = float(f1.get("money", 0) or 0)
        
        inv0 = dict(f0.get("inventory", {}) or {})
        inv1 = dict(f1.get("inventory", {}) or {})
        
        straw0 = int(inv0.get("STRAWBERRY", 0) or 0)
        straw1 = int(inv1.get("STRAWBERRY", 0) or 0)

        p_straw = float(prices.get("STRAWBERRY", 120) or 120)
        p_milk = float(prices.get("MILK", 120) or 120)

        # Track actions
        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        # Detect any market order differences
        mkt_orders0 = a0.get("market", []) if isinstance(a0, dict) else []
        mkt_orders1 = a1.get("market", []) if isinstance(a1, dict) else []

        cash_delta = c0 - c1

        # Check for first persistent cash delta > $50 or action difference
        if first_divergence is None and (abs(cash_delta) > 50.0 or mkt_orders0 != mkt_orders1):
            first_divergence = step
            divergence_details = {
                "step": step,
                "day": step // 24,
                "hero_cash": c0, "opp_cash": c1, "cash_delta": cash_delta,
                "hero_orders": mkt_orders0, "opp_orders": mkt_orders1,
                "hero_shed": inv0, "opp_shed": inv1,
                "p_straw": p_straw, "p_milk": p_milk,
            }

        if step % 24 == 0 or step >= 690:
            step_log.append({
                "step": step, "day": step // 24,
                "hero_cash": c0, "opp_cash": c1, "cash_delta": cash_delta,
                "hero_straw": straw0, "opp_straw": straw1,
                "p_straw": p_straw, "p_milk": p_milk,
                "hero_workers": len(f0.get("workers", []) or []),
                "opp_workers": len(f1.get("workers", []) or []),
            })

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "seed": seed, "seat": seat,
        "hero_reward": r0, "opp_reward": r1, "won": r0 > r1, "margin": r0 - r1,
        "first_divergence_step": first_divergence,
        "divergence_details": divergence_details,
        "checkpoint_log": step_log,
    }

def main():
    print("=" * 145)
    print("EXP163: REAL-META FORENSIC DIVERGENCE MINER ACROSS 20 STRAWBERRY DUOPOLY MATCHES")
    print("=" * 145)

    results = []
    t0 = time.time()

    for i, seed in enumerate(MIRROR_SEEDS):
        seat = 0 if i < 10 else 1
        res = mine_mirror_match_telemetry(seed, seat)
        results.append(res)
        div = res["divergence_details"]
        div_str = f"Step {res['first_divergence_step']} (Day {res['first_divergence_step']//24 if res['first_divergence_step'] else 'None'})"
        won_str = "WIN 🏆" if res["won"] else "LOSS ❌"
        print(f"Match [{i+1:2d}/20] Seed {seed:5d} (Seat {seat}): {won_str} | Margin: ${res['margin']:+10,.2f} | Earliest Divergence: {div_str}")

    elapsed = time.time() - t0
    print(f"\nMined 20 duopoly matches in {elapsed:.1f}s. Synthesizing structural divergence patterns...")

    # Aggregate earliest divergence steps
    divergence_steps = [r["first_divergence_step"] for r in results if r["first_divergence_step"] is not None]
    
    print("\n" + "=" * 145)
    print(f"{'Seed':<8} | {'Seat':<5} | {'Final Margin ($)':<18} | {'First Div Step':<16} | {'Hero Orders at Div':<40} | {'Opp Orders at Div'}")
    print("-" * 145)

    divergence_types = {}
    for r in results:
        div = r["divergence_details"]
        if div:
            step_val = div["step"]
            h_ord = str(div["hero_orders"])
            o_ord = str(div["opp_orders"])
            if h_ord != o_ord:
                d_type = "ACTION_MISMATCH"
            else:
                d_type = "SHARED_MARKET_FILL_ASYMMETRY"
            divergence_types[d_type] = divergence_types.get(d_type, 0) + 1
            print(f"{r['seed']:<8} | {r['seat']:<5} | ${r['margin']:+14,.2f}   | Step {step_val:4d} (Day {step_val//24:2d}) | {h_ord[:38]:<40} | {o_ord[:38]}")

    print("=" * 145)
    print("DIVERGENCE ROOT CAUSE DISTRIBUTION:")
    for dt, count in divergence_types.items():
        print(f"  {dt:<35} : {count:2d} / {len(results)} matches ({count/len(results)*100:.1f}%)")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp163_mirror_divergence_miner_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved Complete EXP163 Telemetry Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
