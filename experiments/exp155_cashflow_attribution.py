"""EXP155: Causal Cash-Flow Attribution Engine across Days 1-15 (Steps 0-360)."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
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

def run_match_cashflow_trace(seed: int, seat: int, b_key: str):
    opp_entry = POPULATION_SUITE[b_key]
    opp_fn = opp_entry["agent"]
    tier = opp_entry["tier"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    # Cashflow ledgers for Days 1-15 (Steps 0 to 360)
    # Track inflows and outflows separately
    h_inflows = {"STRAWBERRY": 0.0, "MILK": 0.0, "WOOL": 0.0, "FERTILIZER": 0.0, "WHEAT": 0.0, "CARROT": 0.0, "MELON": 0.0}
    o_inflows = {"STRAWBERRY": 0.0, "MILK": 0.0, "WOOL": 0.0, "FERTILIZER": 0.0, "WHEAT": 0.0, "CARROT": 0.0, "MELON": 0.0}

    h_outflows = {"SEEDS": 0.0, "ANIMALS": 0.0, "LAND": 0.0, "WAGES": 0.0, "FEED": 0.0}
    o_outflows = {"SEEDS": 0.0, "ANIMALS": 0.0, "LAND": 0.0, "WAGES": 0.0, "FEED": 0.0}

    h_quantities_sold = {"STRAWBERRY": 0, "MILK": 0, "WOOL": 0, "FERTILIZER": 0, "WHEAT": 0}
    o_quantities_sold = {"STRAWBERRY": 0, "MILK": 0, "WOOL": 0, "FERTILIZER": 0, "WHEAT": 0}

    # Step-by-step cash tracking
    h_cash_history = []
    o_cash_history = []

    # Checkpoints at Day 6 (Step 144), Day 9 (Step 216), Day 12 (Step 288), Day 15 (Step 360)
    checkpoints = {}

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation if seat == 0 else env.state[1].observation
        obs1 = env.state[1].observation if seat == 0 else env.state[0].observation

        f0 = obs0.get("farms", [{}, {}])[0]
        f1 = obs1.get("farms", [{}, {}])[0]
        mkt = obs0.get("market", {})
        prices = mkt.get("prices", {})

        c0 = float(f0.get("money", 0))
        c1 = float(f1.get("money", 0))
        h_cash_history.append(c0)
        o_cash_history.append(c1)

        if step in [144, 216, 288, 360]:
            day = step // 24
            checkpoints[f"Day_{day}"] = {
                "step": step,
                "h_cash": c0, "o_cash": c1, "lead": c0 - c1,
                "h_inflows": dict(h_inflows), "o_inflows": dict(o_inflows),
                "h_outflows": dict(h_outflows), "o_outflows": dict(o_outflows),
                "h_qty_sold": dict(h_quantities_sold), "o_qty_sold": dict(o_quantities_sold),
            }

        a0 = sub_d1.agent(obs0, env.configuration)
        try: a1 = opp_fn(obs1, env.configuration)
        except TypeError: a1 = opp_fn(obs1)

        if step <= 360:
            # Audit market orders
            m0 = a0.get("market", []) if isinstance(a0, dict) else []
            m1 = a1.get("market", []) if isinstance(a1, dict) else []

            # Process Hero market transactions
            for o in m0:
                if isinstance(o, (list, tuple)) and len(o) >= 1:
                    cmd = o[0]
                    if cmd == "SELL" and len(o) >= 3:
                        item = o[1]
                        qty = int(o[2])
                        p = float(prices.get(item, 0.0))
                        rev = qty * p
                        h_inflows[item] = h_inflows.get(item, 0.0) + rev
                        h_quantities_sold[item] = h_quantities_sold.get(item, 0) + qty
                    elif cmd == "BUY_SEED" and len(o) >= 3:
                        crop = o[1]
                        qty = int(o[2])
                        cost = qty * (25.0 if crop == "STRAWBERRY" else 10.0)
                        h_outflows["SEEDS"] += cost
                    elif cmd == "BUY_ANIMAL" and len(o) >= 2:
                        cost = 1000.0 if o[1] == "COW" else (500.0 if o[1] == "SHEEP" else 200.0)
                        h_outflows["ANIMALS"] += cost
                    elif cmd == "BUY_LAND":
                        h_outflows["LAND"] += 1000.0
                    elif cmd == "HIRE":
                        h_outflows["WAGES"] += 500.0

            # Process Opponent market transactions
            for o in m1:
                if isinstance(o, (list, tuple)) and len(o) >= 1:
                    cmd = o[0]
                    if cmd == "SELL" and len(o) >= 3:
                        item = o[1]
                        qty = int(o[2])
                        p = float(prices.get(item, 0.0))
                        rev = qty * p
                        o_inflows[item] = o_inflows.get(item, 0.0) + rev
                        o_quantities_sold[item] = o_quantities_sold.get(item, 0) + qty
                    elif cmd == "BUY_SEED" and len(o) >= 3:
                        crop = o[1]
                        qty = int(o[2])
                        cost = qty * (25.0 if crop == "STRAWBERRY" else 10.0)
                        o_outflows["SEEDS"] += cost
                    elif cmd == "BUY_ANIMAL" and len(o) >= 2:
                        cost = 1000.0 if o[1] == "COW" else (500.0 if o[1] == "SHEEP" else 200.0)
                        o_outflows["ANIMALS"] += cost
                    elif cmd == "BUY_LAND":
                        o_outflows["LAND"] += 1000.0
                    elif cmd == "HIRE":
                        o_outflows["WAGES"] += 500.0

        env.step([a0, a1] if seat == 0 else [a1, a0])

    r0 = float(env.state[seat].reward or 0.0)
    r1 = float(env.state[1 - seat].reward or 0.0)

    return {
        "bot_key": b_key, "tier": tier, "seed": seed, "seat": seat,
        "hero_reward": r0, "opp_reward": r1, "won": r0 > r1,
        "checkpoints": checkpoints,
        "h_inflows_total": h_inflows, "o_inflows_total": o_inflows,
        "h_outflows_total": h_outflows, "o_outflows_total": o_outflows,
        "h_qty_sold_total": h_quantities_sold, "o_qty_sold_total": o_quantities_sold,
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        bot_keys = sys.argv[2].split(",")
        worker_id = sys.argv[3]
        seeds = [1000, 42, 100, 200, 300, 500, 1001, 20042, 12345, 54321,
                 20001, 20010, 20020, 20030, 20040, 20050, 20060, 20070, 20080, 20090]
        results = []
        for b_key in bot_keys:
            if b_key not in POPULATION_SUITE: continue
            for i, seed in enumerate(seeds):
                seat = 0 if i < 10 else 1
                res = run_match_cashflow_trace(seed, seat, b_key)
                results.append(res)
        out_file = os.path.join(REPORTS_DIR, f"exp155_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    # Master Runner Mode
    print("=" * 145)
    print("EXP155: CAUSAL CASH-FLOW ATTRIBUTION (DAYS 1-15 / 200 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.abspath(__file__), "--worker", chunk_str, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, chunk, worker_id))
        print(f"  Launched Worker {idx} for archetypes: {chunk} (PID: {p.pid})")

    for p, chunk, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating cash-flow ledgers...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp155_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Day 6, Day 9, Day 12, Day 15 Cashflow Decomposition
    print("\n" + "=" * 145)
    print("DAYS 6-15 CASHFLOW DECOMPOSITION SUMMARY (HERO D.1 VS LADDER POPULATION):")
    print("=" * 145)

    for day_label in ["Day_6", "Day_9", "Day_12", "Day_15"]:
        print(f"\n>>> CHECKPOINT: {day_label} <<<")
        print(f"{'Opponent Archetype':<24} | {'Hero Cash':<12} | {'Opp Cash':<12} | {'Net Lead ($)':<14} | {'Delta Strawberry Rev':<22} | {'Delta Milk Rev':<16} | {'Delta Capital Exp'}")
        print("-" * 145)

        for b_key in all_keys:
            sub = [d for d in all_data if d["bot_key"] == b_key]
            if not sub: continue

            h_c = np.mean([d["checkpoints"][day_label]["h_cash"] for d in sub])
            o_c = np.mean([d["checkpoints"][day_label]["o_cash"] for d in sub])
            lead = h_c - o_c

            d_straw = np.mean([d["checkpoints"][day_label]["h_inflows"].get("STRAWBERRY", 0) - d["checkpoints"][day_label]["o_inflows"].get("STRAWBERRY", 0) for d in sub])
            d_milk = np.mean([d["checkpoints"][day_label]["h_inflows"].get("MILK", 0) - d["checkpoints"][day_label]["o_inflows"].get("MILK", 0) for d in sub])
            
            h_exp = np.mean([sum(d["checkpoints"][day_label]["h_outflows"].values()) for d in sub])
            o_exp = np.mean([sum(d["checkpoints"][day_label]["o_outflows"].values()) for d in sub])
            d_exp = h_exp - o_exp

            print(f"{b_key:<24} | ${h_c:10,.2f} | ${o_c:10,.2f} | ${lead:+12,.2f} | ${d_straw:+20,.2f} | ${d_milk:+14,.2f} | ${d_exp:+16,.2f}")

    out_json = os.path.join(REPORTS_DIR, "exp155_cashflow_attribution_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP155 Cashflow Attribution Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
