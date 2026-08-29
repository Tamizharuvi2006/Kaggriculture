"""EXP152 Multi-Process Runner: Evaluates Arms A, B, C across the 10-archetype population benchmark."""
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
    print("EXP152: STEP-696 ORDER-PRIORITY BENCHMARK (ARMS A, B, C ACROSS 10 ARCHETYPES / 600 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp152_worker.py"), chunk_str, worker_id]
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
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating results...")

    all_data = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp152_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    # 1. Stratified Scorecard by Archetype
    print("\n" + "=" * 145)
    print(f"{'Opponent Key':<24} | {'Tier':<25} | {'Arm A WR':<10} | {'Arm B WR':<10} | {'Arm C WR':<10} | {'Delta B-A ($)':<16} | {'Delta C-A ($)'}")
    print("=" * 145)

    archetype_summaries = {}
    tier_groups = {}

    for b_key in all_keys:
        sub_items = [d for d in all_data if d["bot_key"] == b_key]
        n = len(sub_items)
        if n == 0: continue

        n_a = sum(1 for d in sub_items if d["arm_a"]["won"])
        n_b = sum(1 for d in sub_items if d["arm_b"]["won"])
        n_c = sum(1 for d in sub_items if d["arm_c"]["won"])

        d_b = float(np.mean([d["delta_b_vs_a"] for d in sub_items]))
        d_c = float(np.mean([d["delta_c_vs_a"] for d in sub_items]))

        tier = sub_items[0]["tier"]
        archetype = sub_items[0]["archetype"]

        archetype_summaries[b_key] = {
            "tier": tier, "archetype": archetype,
            "matches": n,
            "wr_a": (n_a / n) * 100, "wr_b": (n_b / n) * 100, "wr_c": (n_c / n) * 100,
            "delta_b": d_b, "delta_c": d_c,
        }

        if tier not in tier_groups: tier_groups[tier] = []
        tier_groups[tier].extend(sub_items)

        print(f"{b_key:<24} | {tier:<25} | {(n_a/n)*100:5.1f}%    | {(n_b/n)*100:5.1f}%    | {(n_c/n)*100:5.1f}%    | ${d_b:+13,.2f}  | ${d_c:+13,.2f}")

    # 2. Stratified Scorecard by Tier
    print("\n" + "=" * 145)
    print(f"{'Tier Group':<30} | {'Total Matches':<14} | {'Arm A WR':<12} | {'Arm B WR':<12} | {'Arm C WR':<12} | {'Mean Delta B ($)':<18} | {'Mean Delta C ($)'}")
    print("=" * 145)

    tier_summaries = {}
    for tier_name, t_items in tier_groups.items():
        n_t = len(t_items)
        n_a_t = sum(1 for d in t_items if d["arm_a"]["won"])
        n_b_t = sum(1 for d in t_items if d["arm_b"]["won"])
        n_c_t = sum(1 for d in t_items if d["arm_c"]["won"])

        t_db = float(np.mean([d["delta_b_vs_a"] for d in t_items]))
        t_dc = float(np.mean([d["delta_c_vs_a"] for d in t_items]))

        tier_summaries[tier_name] = {
            "matches": n_t,
            "wr_a": (n_a_t / n_t) * 100, "wr_b": (n_b_t / n_t) * 100, "wr_c": (n_c_t / n_t) * 100,
            "delta_b": t_db, "delta_c": t_dc,
        }

        print(f"{tier_name:<30} | {n_t:<14} | {(n_a_t/n_t)*100:5.1f}%      | {(n_b_t/n_t)*100:5.1f}%      | {(n_c_t/n_t)*100:5.1f}%      | ${t_db:+15,.2f}  | ${t_dc:+15,.2f}")

    # Overall Summary
    total_n = len(all_data)
    tot_a_wins = sum(1 for d in all_data if d["arm_a"]["won"])
    tot_b_wins = sum(1 for d in all_data if d["arm_b"]["won"])
    tot_c_wins = sum(1 for d in all_data if d["arm_c"]["won"])

    mean_d_b = float(np.mean([d["delta_b_vs_a"] for d in all_data]))
    mean_d_c = float(np.mean([d["delta_c_vs_a"] for d in all_data]))

    overall_wr_a = (tot_a_wins / total_n) * 100
    overall_wr_b = (tot_b_wins / total_n) * 100
    overall_wr_c = (tot_c_wins / total_n) * 100

    print("-" * 145)
    print(f"{'OVERALL POPULATION BASKET':<30} | {total_n:<14} | {overall_wr_a:5.1f}%      | {overall_wr_b:5.1f}%      | {overall_wr_c:5.1f}%      | ${mean_d_b:+15,.2f}  | ${mean_d_c:+15,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp152_order_priority_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "total_matches": total_n,
                "wr_a": _to_native(overall_wr_a), "wr_b": _to_native(overall_wr_b), "wr_c": _to_native(overall_wr_c),
                "mean_delta_b": _to_native(mean_d_b), "mean_delta_c": _to_native(mean_d_c),
            },
            "by_tier": _to_native(tier_summaries),
            "by_archetype": _to_native(archetype_summaries),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP152 Order Priority Benchmark Dataset: {out_json}")

if __name__ == "__main__":
    main()
