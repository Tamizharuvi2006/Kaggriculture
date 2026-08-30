"""EXP164: Order-Priority Reality Audit & Timing Perturbation Engine."""
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

SEEDS = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
         20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]

def run_timing_perturbation_match(seed: int, seat: int, mode: str):
    """
    mode:
      - 'baseline': D.1 unmodified
      - 'delay_sell_1': Delay market sell orders by 1 step
      - 'advance_sell_1': Flush sell orders 1 step earlier when inventory exists
      - 'half_qty_sell': Split sell orders into half-size batches
    """
    opp_fn = POPULATION_SUITE["T1_v18_mirror"]["agent"]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    delayed_orders = []

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        a0 = sub_d1.agent(obs0, env.configuration)
        
        if isinstance(a0, dict):
            m = a0.get("market", []) or []
            if mode == "delay_sell_1":
                # Delay any SELL orders to next step
                sells = [o for o in m if isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL"]
                non_sells = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL")]
                to_execute = non_sells + delayed_orders
                delayed_orders = sells
                a0["market"] = to_execute[:10]
            elif mode == "half_qty_sell":
                new_m = []
                for o in m:
                    if isinstance(o, (list, tuple)) and len(o) >= 3 and o[0] == "SELL":
                        new_m.append(["SELL", o[1], max(1, int(o[2]) // 2)])
                    else:
                        new_m.append(o)
                a0["market"] = new_m[:10]
            elif mode == "advance_sell_1":
                # If inventory >= 2 and not selling, advance sell
                f = obs0.get("farms", [{}, {}])[0]
                shed = f.get("inventory", {}) or {}
                straw = int(shed.get("STRAWBERRY", 0) or 0)
                if straw >= 2 and not any(isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == "SELL" for o in m):
                    m.append(["SELL", "STRAWBERRY", straw])
                a0["market"] = m[:10]

        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)
    return {"hero": r0, "opp": r1, "margin": r0 - r1, "won": r0 > r1}

def audit_order_priority():
    print("=" * 145)
    print("EXP164: ORDER-PRIORITY REALITY AUDIT & DETERMINISTIC TIMING PERTURBATION TEST")
    print("=" * 145)

    # 1. Engine Verification Summary
    print("1. KAGGRICULTURE ENGINE MARKET PROCESSING AUDIT:")
    print("   - Source File: kaggle_environments/envs/kaggriculture/kaggriculture.py (lines 544-625)")
    print("   - Commodity Markets (SELL / BUY_PRODUCT / BUY_SEED / BUY_ANIMAL):")
    print("     * Implements 'Per-Unit Lockstep Quoting' (lines 590-618).")
    print("     * When Player 0 and Player 1 submit SELL orders on the SAME step, BOTH players receive the EXACT same quoted price per unit.")
    print("     * Price decrements sequentially unit-by-unit in parallel (no first-player price grab within the same step).")
    print("   - Atomic Operations (HIRE / BUY_LAND):")
    print("     * Executed strictly in player_id order (Player 0 then Player 1) (lines 572-581).")
    print("   - Cross-Step Order Lag:")
    print("     * If Player A sells at Step t and Player B sells at Step t+1, Player B receives the post-drop depressed price.")

    # 2. Benchmark Modes Across 20 Seeds
    modes = ["baseline", "delay_sell_1", "advance_sell_1", "half_qty_sell"]
    summary_results = {}

    for mode in modes:
        t0 = time.time()
        results = []
        for i, seed in enumerate(SEEDS):
            seat = 0 if i < 10 else 1
            res = run_timing_perturbation_match(seed, seat, mode)
            results.append(res)
        
        elapsed = time.time() - t0
        wr = sum(1 for r in results if r["won"]) / len(results) * 100
        mean_hero = np.mean([r["hero"] for r in results])
        mean_opp = np.mean([r["opp"] for r in results])
        mean_margin = np.mean([r["margin"] for r in results])

        summary_results[mode] = {
            "win_rate": wr,
            "wins": sum(1 for r in results if r["won"]),
            "mean_hero": float(mean_hero),
            "mean_opp": float(mean_opp),
            "mean_margin": float(mean_margin),
            "elapsed_s": float(elapsed),
        }

    print("\n" + "=" * 145)
    print(f"{'Perturbation Mode':<25} | {'Mean Reward ($)':<18} | {'Opp Mean ($)':<18} | {'Mean Margin ($)':<20} | {'Win Rate (20 Seeds)'}")
    print("-" * 145)
    for mode, data in summary_results.items():
        print(f"{mode:<25} | ${data['mean_hero']:14,.2f}   | ${data['mean_opp']:14,.2f}   | ${data['mean_margin']:+16,.2f}   | {data['win_rate']:5.1f}% ({data['wins']:2d}/20)")
    print("=" * 145)

    # 3. Seat Asymmetry Audit
    print("\n3. SEAT ASYMMETRY AUDIT (BASELINE D.1 VS V18):")
    seat0_matches = [run_timing_perturbation_match(seed, 0, "baseline") for seed in SEEDS[:10]]
    seat1_matches = [run_timing_perturbation_match(seed, 1, "baseline") for seed in SEEDS[10:]]

    wr_seat0 = sum(1 for r in seat0_matches if r["won"]) / len(seat0_matches) * 100
    wr_seat1 = sum(1 for r in seat1_matches if r["won"]) / len(seat1_matches) * 100
    margin_seat0 = np.mean([r["margin"] for r in seat0_matches])
    margin_seat1 = np.mean([r["margin"] for r in seat1_matches])

    print(f"   Seat 0 (Player 0): Win Rate = {wr_seat0:5.1f}% ({sum(1 for r in seat0_matches if r['won'])}/10) | Mean Margin = ${margin_seat0:+10,.2f}")
    print(f"   Seat 1 (Player 1): Win Rate = {wr_seat1:5.1f}% ({sum(1 for r in seat1_matches if r['won'])}/10) | Mean Margin = ${margin_seat1:+10,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp164_order_priority_audit_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "engine_audit": {
                "per_unit_lockstep": True,
                "same_step_price_equality": True,
                "atomic_order_player0_first": True,
            },
            "perturbation_modes": summary_results,
            "seat_asymmetry": {
                "seat0_wr": wr_seat0,
                "seat0_margin": float(margin_seat0),
                "seat1_wr": wr_seat1,
                "seat1_margin": float(margin_seat1),
            }
        }, f, indent=2)

    print(f"Saved Complete EXP164 Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    audit_order_priority()
