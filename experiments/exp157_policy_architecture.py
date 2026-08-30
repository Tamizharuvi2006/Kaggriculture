"""EXP157: State-Conditioned Policy Architecture & Regime Mining Engine."""
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

def mine_state_action_transitions(seed: int, seat: int, b_key: str):
    opp_entry = POPULATION_SUITE[b_key]
    opp_fn = opp_entry["agent"]
    tier = opp_entry["tier"]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    # Telemetry registers for state-action divergence mining
    regime_events = []
    
    # Trackers
    prev_prices = {}

    while not env.done:
        step = env.state[0].observation.get("step", 0)
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation

        h_obs = obs0 if seat == 0 else obs1
        o_obs = obs1 if seat == 0 else obs0

        h_farm = h_obs.get("farms", [{}, {}])[seat]
        o_farm = o_obs.get("farms", [{}, {}])[1 - seat]

        mkt = h_obs.get("market", {})
        prices = mkt.get("prices", {})
        
        # State variables legally visible
        h_cash = float(h_farm.get("money", 0.0))
        o_cash = float(o_farm.get("money", 0.0))
        
        # Public opponent farm tiles
        o_tiles = o_farm.get("tiles", [])
        o_straw_tiles = sum(1 for r in o_tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        o_cows = sum(1 for r in o_tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
        o_sheep = sum(1 for r in o_tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")

        # Own farm state
        h_tiles = h_farm.get("tiles", [])
        h_straw_tiles = sum(1 for r in h_tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        h_cows = sum(1 for r in h_tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")

        # Price velocities
        p_straw = float(prices.get("STRAWBERRY", 120.0))
        p_milk = float(prices.get("MILK", 120.0))
        p_straw_vel = p_straw - prev_prices.get("STRAWBERRY", p_straw)
        prev_prices = dict(prices)

        a_h = sub_d1.agent(h_obs, env.configuration)
        try: a_o = opp_fn(o_obs, env.configuration)
        except TypeError: a_o = opp_fn(o_obs)

        m0 = a_h.get("market", []) if isinstance(a_h, dict) else []
        m1 = a_o.get("market", []) if isinstance(a_o, dict) else []

        # Classify regime triggers
        # Regime 1: Capital Liquidity Threshold / Solvency Stress
        if h_cash < 500.0 or o_cash < 500.0:
            regime_events.append({
                "step": step, "day": step // 24, "regime": "LIQUIDITY_STRESS",
                "h_cash": h_cash, "o_cash": o_cash,
                "h_orders": m0, "o_orders": m1,
                "diff": m0 != m1
            })

        # Regime 2: Strawberry Rebound / Price Velocity Dip
        if p_straw < 135.0 or p_straw_vel < -5.0:
            regime_events.append({
                "step": step, "day": step // 24, "regime": "PRICE_DIP_STRAWBERRY",
                "p_straw": p_straw, "p_straw_vel": p_straw_vel,
                "h_orders": m0, "o_orders": m1,
                "diff": m0 != m1
            })

        # Regime 3: High Reinvestment Solvency (Cash > 2500, Land Capex Opportunity)
        if h_cash >= 2000.0 or o_cash >= 2000.0:
            regime_events.append({
                "step": step, "day": step // 24, "regime": "HIGH_SOLVENCY_EXPANSION",
                "h_cash": h_cash, "o_cash": o_cash,
                "h_orders": m0, "o_orders": m1,
                "diff": m0 != m1
            })

        # Regime 4: Opponent Mirror / Agro-Industrial Competition
        if o_straw_tiles >= 8 and o_cows >= 4:
            regime_events.append({
                "step": step, "day": step // 24, "regime": "MIRROR_DUOPOLY",
                "o_straw": o_straw_tiles, "o_cows": o_cows,
                "h_orders": m0, "o_orders": m1,
                "diff": m0 != m1
            })

        if step >= 360:
            break

        env.step([a_h, a_o] if seat == 0 else [a_o, a_h])

    return {
        "bot_key": b_key, "tier": tier, "seed": seed, "seat": seat,
        "total_events": len(regime_events),
        "events": regime_events[:100], # sample representative transitions
    }

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        b_key = sys.argv[2]
        worker_id = sys.argv[3]
        seeds = [1000, 42]
        results = []
        for i, seed in enumerate(seeds):
            seat = 0 if i == 0 else 1
            res = mine_state_action_transitions(seed, seat, b_key)
            results.append(res)
        out_file = os.path.join(REPORTS_DIR, f"exp157_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] completed -> {out_file}")
        return

    print("=" * 145)
    print("EXP157: STATE-CONDITIONED POLICY ARCHITECTURE & REGIME FORENSICS")
    print("=" * 145)

    archetypes_to_test = [
        "T1_v18_mirror",
        "T1_carrot_rusher",
        "T2_dynamic_v81",
        "T3_high_yield_v83",
        "T4_experimental_v84"
    ]

    processes = []
    t0 = time.time()

    for idx, b_key in enumerate(archetypes_to_test):
        worker_id = f"worker_{idx}"
        cmd = [sys.executable, os.path.abspath(__file__), "--worker", b_key, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, b_key, worker_id))
        print(f"  Launched Worker {idx} for archetype: {b_key} (PID: {p.pid})")

    for p, b_key, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f}s. Synthesizing regime transitions...")

    all_results = []
    for idx in range(len(archetypes_to_test)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp157_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results.extend(data)
            os.remove(part_file)

    out_json = os.path.join(REPORTS_DIR, "exp157_policy_architecture_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nSaved Complete EXP157 Policy Architecture Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
