"""EXP154 Multi-Process Runner: Day-30 Labor EV Mining across Population Basket."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

from benchmark.population_suite import POPULATION_SUITE

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

def main():
    print("=" * 145)
    print("EXP154: DAY-30 LABOR VALUE SWEEP & DECISION MODELING (N=0..10 ACROSS 10 ARCHETYPES / 200 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp154_worker.py"), chunk_str, worker_id]
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
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating EV distributions...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp154_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Distribution of Optimal N*
    print("\n" + "=" * 145)
    print("1. DISTRIBUTION OF OPTIMAL DAY-30 HIRES (N*) ACROSS 200 MATCH STATES:")
    print("=" * 145)
    n_counts = {n: sum(1 for d in all_data if d["best_n"] == n) for n in [0, 2, 4, 6, 8, 10]}
    for n, cnt in n_counts.items():
        pct = (cnt / len(all_data)) * 100
        print(f"  Optimal N = {n:2d} workers : {cnt:3d} / {len(all_data)} matches ({pct:5.1f}%)")

    # 2. Scorecard by Archetype across N=0, N=2, N=4, N=10
    print("\n" + "=" * 145)
    print(f"{'Opponent Key':<24} | {'Mean Field Potential ($)':<26} | {'Reward N=0 ($)':<16} | {'Reward N=2 ($)':<16} | {'Reward N=4 ($)':<16} | {'Reward N=10 ($)'}")
    print("-" * 145)

    for b_key in all_keys:
        sub_items = [d for d in all_data if d["bot_key"] == b_key]
        if not sub_items: continue
        mean_field = float(np.mean([d["state_at_696"].get("field_potential", 0) for d in sub_items]))
        r_n0 = float(np.mean([d["sweep_rewards"]["N_0"]["reward"] for d in sub_items]))
        r_n2 = float(np.mean([d["sweep_rewards"]["N_2"]["reward"] for d in sub_items]))
        r_n4 = float(np.mean([d["sweep_rewards"]["N_4"]["reward"] for d in sub_items]))
        r_n10 = float(np.mean([d["sweep_rewards"]["N_10"]["reward"] for d in sub_items]))
        print(f"{b_key:<24} | ${mean_field:20,.2f}       | ${r_n0:12,.2f}   | ${r_n2:12,.2f}   | ${r_n4:12,.2f}   | ${r_n10:12,.2f}")

    # 3. Decision Boundary Analysis
    print("\n" + "=" * 145)
    print("3. DECISION BOUNDARY & REGRESSION CORRELATION (FIELD POTENTIAL VS N* EV):")
    print("=" * 145)
    n0_better = [d for d in all_data if d["best_n"] == 0]
    nhire_better = [d for d in all_data if d["best_n"] > 0]

    print(f"  States where N=0 is strictly optimal ({len(n0_better)} matches):")
    print(f"    Mean Unharvested Field Potential = ${np.mean([d['state_at_696'].get('field_potential', 0) for d in n0_better]):,.2f}")
    print(f"    Mean Ripe Strawberries in Field  = {np.mean([d['state_at_696'].get('ripe_straw', 0) for d in n0_better]):.2f} tiles")

    if nhire_better:
        print(f"  States where N > 0 is strictly optimal ({len(nhire_better)} matches):")
        print(f"    Mean Unharvested Field Potential = ${np.mean([d['state_at_696'].get('field_potential', 0) for d in nhire_better]):,.2f}")
        print(f"    Mean Ripe Strawberries in Field  = {np.mean([d['state_at_696'].get('ripe_straw', 0) for d in nhire_better]):.2f} tiles")

    out_json = os.path.join(REPORTS_DIR, "exp154_day30_value_miner_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_matches": len(all_data),
            "n_counts": _to_native(n_counts),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP154 Day-30 Labor EV Dataset: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
