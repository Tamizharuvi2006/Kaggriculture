"""EXP137 Multi-Process Runner: Evaluates Arm A vs Arm B vs Arm C across 5 distinct opponent bots."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

OPPONENTS = [
    "kaitofukami-v18.py",
    "submission_v81.py",
    "submission_v82.py",
    "submission_v83.py",
    "submission_v83_opponent_aware.py",
]

def main():
    print("=" * 135)
    print("EXP137: MULTI-OPPONENT ADAPTIVE LABOR GATE BENCHMARK (300 TOTAL MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    processes = []
    t0 = time.time()

    for idx, bot_file in enumerate(OPPONENTS):
        worker_id = f"opp_{idx}_{bot_file.split('.')[0]}"
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp137_worker.py"), bot_file, worker_id]
        p = subprocess.Popen(cmd)
        processes.append((p, bot_file, worker_id))
        print(f"  Launched worker for {bot_file} (Worker ID: {worker_id}, PID: {p.pid})")

    for p, bot_file, worker_id in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{worker_id}] failed with code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{worker_id}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating results...")

    all_data = []
    for idx, bot_file in enumerate(OPPONENTS):
        worker_id = f"opp_{idx}_{bot_file.split('.')[0]}"
        part_file = os.path.join(REPORTS_DIR, f"exp137_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    df = pd.DataFrame(all_data)

    print("\n" + "=" * 135)
    print(f"{'Opponent Architecture':<35} | {'Arm A WR':<10} | {'Arm B WR':<10} | {'Arm C WR':<10} | {'Mean Delta B-A':<15} | {'Mean Delta C-A':<15} | {'C vs B Delta'}")
    print("=" * 135)

    opp_summaries = {}
    for opp_name in OPPONENTS:
        sub_df = df[df["opponent"] == opp_name]
        n = len(sub_df)
        wr_a = sub_df["won_a"].mean() * 100
        wr_b = sub_df["won_b"].mean() * 100
        wr_c = sub_df["won_c"].mean() * 100
        delta_b = sub_df["delta_b_vs_a"].mean()
        delta_c = sub_df["delta_c_vs_a"].mean()
        delta_cb = sub_df["delta_c_vs_b"].mean()

        opp_summaries[opp_name] = {
            "matches": n,
            "wr_a": wr_a, "wr_b": wr_b, "wr_c": wr_c,
            "delta_b_vs_a": delta_b, "delta_c_vs_a": delta_c,
            "delta_c_vs_b": delta_cb,
        }
        print(f"{opp_name:<35} | {wr_a:5.1f}%     | {wr_b:5.1f}%     | {wr_c:5.1f}%     | ${delta_b:+13,.2f} | ${delta_c:+13,.2f} | ${delta_cb:+10,.2f}")

    print("-" * 135)
    overall_wr_a = df["won_a"].mean() * 100
    overall_wr_b = df["won_b"].mean() * 100
    overall_wr_c = df["won_c"].mean() * 100
    overall_delta_b = df["delta_b_vs_a"].mean()
    overall_delta_c = df["delta_c_vs_a"].mean()
    overall_delta_cb = df["delta_c_vs_b"].mean()

    print(f"{'OVERALL (100 MATCHES / ARM)':<35} | {overall_wr_a:5.1f}%     | {overall_wr_b:5.1f}%     | {overall_wr_c:5.1f}%     | ${overall_delta_b:+13,.2f} | ${overall_delta_c:+13,.2f} | ${overall_delta_cb:+10,.2f}")
    print("=" * 135)

    out_json = os.path.join(REPORTS_DIR, "exp137_multi_opponent_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "wr_a": _to_native(overall_wr_a),
                "wr_b": _to_native(overall_wr_b),
                "wr_c": _to_native(overall_wr_c),
                "delta_b_vs_a": _to_native(overall_delta_b),
                "delta_c_vs_a": _to_native(overall_delta_c),
                "delta_c_vs_b": _to_native(overall_delta_cb),
            },
            "by_opponent": _to_native(opp_summaries),
            "all_matches": _to_native(all_data),
        }, f, indent=2)
    print(f"\nSaved Complete EXP137 Multi-Opponent Benchmark Results: {out_json}")

if __name__ == "__main__":
    main()
