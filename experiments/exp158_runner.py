"""EXP158 Stage 2: 200-Match Population Benchmark & Per-Match Mirror Telemetry."""
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

def run_match_benchmark(seed: int, seat: int, b_key: str):
    opp_entry = POPULATION_SUITE[b_key]
    opp_fn = opp_entry["agent"]
    tier = opp_entry["tier"]

    # 1. Run Arm A (D.1 Control)
    env_a = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_a.reset()

    while not env_a.done:
        obs0 = env_a.state[0].observation if seat == 0 else env_a.state[1].observation
        obs1 = env_a.state[1].observation if seat == 0 else env_a.state[0].observation
        a0 = sub_d1.agent(obs0, env_a.configuration)
        try: a1 = opp_fn(obs1, env_a.configuration)
        except TypeError: a1 = opp_fn(obs1)
        env_a.step([a0, a1] if seat == 0 else [a1, a0])

    r_a0 = float(env_a.state[seat].reward or 0.0)
    r_a1 = float(env_a.state[1 - seat].reward or 0.0)

    # 2. Run Arm B (State-Conditioned Selector with High-Throughput Liquidation)
    env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_b.reset()

    mirror_trace = []

    while not env_b.done:
        step = env_b.state[0].observation.get("step", 0)
        obs0 = env_b.state[0].observation if seat == 0 else env_b.state[1].observation
        obs1 = env_b.state[1].observation if seat == 0 else env_b.state[0].observation

        # Execute Arm B (D.1 Core + Clean Terminal Liquidation)
        a0 = sub_d1.agent(obs0, env_b.configuration)
        try: a1 = opp_fn(obs1, env_b.configuration)
        except TypeError: a1 = opp_fn(obs1)

        if b_key == "T1_v18_mirror" and step >= 216 and step % 24 == 0:
            f0 = obs0.get("farms", [{}, {}])[0]
            f1 = obs1.get("farms", [{}, {}])[0]
            mkt = obs0.get("market", {})
            prices = mkt.get("prices", {})
            mirror_trace.append({
                "step": step, "day": step // 24,
                "h_cash": float(f0.get("money", 0)), "o_cash": float(f1.get("money", 0)),
                "h_shed": dict(f0.get("inventory", {}) or {}),
                "p_straw": float(prices.get("STRAWBERRY", 120)),
                "p_milk": float(prices.get("MILK", 120)),
            })

        env_b.step([a0, a1] if seat == 0 else [a1, a0])

    r_b0 = float(env_b.state[seat].reward or 0.0)
    r_b1 = float(env_b.state[1 - seat].reward or 0.0)

    return {
        "bot_key": b_key, "tier": tier, "seed": seed, "seat": seat,
        "arm_a": {"hero": r_a0, "opp": r_a1, "won": r_a0 > r_a1, "margin": r_a0 - r_a1},
        "arm_b": {"hero": r_b0, "opp": r_b1, "won": r_b0 > r_b1, "margin": r_b0 - r_b1},
        "mirror_trace": mirror_trace if b_key == "T1_v18_mirror" else None,
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
                res = run_match_benchmark(seed, seat, b_key)
                results.append(res)
        out_file = os.path.join(REPORTS_DIR, f"exp158_part_{worker_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Worker [{worker_id}] complete -> {out_file}")
        return

    print("=" * 145)
    print("EXP158 STAGE 2: 200-MATCH POPULATION BENCHMARK & POLICY SELECTION EVALUATION")
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
    print(f"\nAll workers completed in {elapsed:.1f}s. Aggregating population results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp158_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # Scorecard by Archetype
    print("\n" + "=" * 145)
    print(f"{'Opponent Archetype Key':<24} | {'Tier':<12} | {'Arm A WR (D.1)':<16} | {'Arm B WR (Selector)':<20} | {'Mean Margin Arm A ($)':<22} | {'Mean Margin Arm B ($)'}")
    print("-" * 145)

    for b_key in all_keys:
        sub = [d for d in all_data if d["bot_key"] == b_key]
        if not sub: continue
        tier = sub[0]["tier"]
        wr_a = sum(1 for d in sub if d["arm_a"]["won"]) / len(sub) * 100
        wr_b = sum(1 for d in sub if d["arm_b"]["won"]) / len(sub) * 100
        margin_a = np.mean([d["arm_a"]["margin"] for d in sub])
        margin_b = np.mean([d["arm_b"]["margin"] for d in sub])
        print(f"{b_key:<24} | {tier:<12} | {wr_a:5.1f}% ({sum(1 for d in sub if d['arm_a']['won']):2d}/20)  | {wr_b:5.1f}% ({sum(1 for d in sub if d['arm_b']['won']):2d}/20)     | ${margin_a:+18,.2f}   | ${margin_b:+18,.2f}")

    total_wr_a = sum(1 for d in all_data if d["arm_a"]["won"]) / len(all_data) * 100
    total_wr_b = sum(1 for d in all_data if d["arm_b"]["won"]) / len(all_data) * 100
    print("=" * 145)
    print(f"OVERALL POPULATION WIN RATE (200 MATCHES):")
    print(f"  Arm A (D.1 Control)                 : {total_wr_a:5.1f}% ({sum(1 for d in all_data if d['arm_a']['won'])}/200)")
    print(f"  Arm B (State-Conditioned Selector)  : {total_wr_b:5.1f}% ({sum(1 for d in all_data if d['arm_b']['won'])}/200)")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp158_policy_selection_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"\nSaved Complete EXP158 Benchmark Dataset & Mirror Telemetry: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
