"""EXP144 Multi-Process Runner: Evaluates Arm A (Control) vs Arm B (Marginal Wheat Retention)."""
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
    print("EXP144: ADAPTIVE WHEAT RETENTION BENCHMARK (ARM A CONTROL VS ARM B MARGINAL RETENTION)")
    print("=" * 135)

    processes = []
    t0 = time.time()

    for idx, bot_file in enumerate(OPPONENTS):
        worker_id = f"opp_{idx}_{bot_file.split('.')[0]}"
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp144_worker.py"), bot_file, worker_id]
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
        part_file = os.path.join(REPORTS_DIR, f"exp144_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    opp_summaries = {}
    print("\n" + "=" * 135)
    print(f"{'Opponent Architecture':<35} | {'Arm A WR':<12} | {'Arm B WR':<12} | {'Delta B-A ($)':<18} | {'Loss -> Win':<12} | {'Win -> Loss'}")
    print("=" * 135)

    total_matches = len(all_data)
    a_wins, b_wins = 0, 0
    tot_d_b = 0.0
    l2w, w2l = 0, 0

    for opp_name in OPPONENTS:
        sub_items = [d for d in all_data if d["opponent"] == opp_name]
        n = len(sub_items)
        if n == 0: continue

        n_a = sum(1 for d in sub_items if d["arm_a"]["won"])
        n_b = sum(1 for d in sub_items if d["arm_b"]["won"])

        d_b = float(np.mean([d["delta_b_vs_a"] for d in sub_items]))
        n_l2w = sum(1 for d in sub_items if not d["arm_a"]["won"] and d["arm_b"]["won"])
        n_w2l = sum(1 for d in sub_items if d["arm_a"]["won"] and not d["arm_b"]["won"])

        a_wins += n_a
        b_wins += n_b
        tot_d_b += sum(d["delta_b_vs_a"] for d in sub_items)
        l2w += n_l2w
        w2l += n_w2l

        opp_summaries[opp_name] = {
            "matches": n,
            "wr_a": (n_a / n) * 100, "wr_b": (n_b / n) * 100,
            "delta_b": d_b, "l2w": n_l2w, "w2l": n_w2l,
        }

        print(f"{opp_name:<35} | {(n_a/n)*100:5.1f}%      | {(n_b/n)*100:5.1f}%      | ${d_b:+15,.2f} | {n_l2w:<12} | {n_w2l}")

    print("-" * 135)
    overall_wr_a = (a_wins / total_matches) * 100
    overall_wr_b = (b_wins / total_matches) * 100
    mean_d_b = tot_d_b / total_matches

    print(f"{'OVERALL (100 MATCHES / ARM)':<35} | {overall_wr_a:5.1f}%      | {overall_wr_b:5.1f}%      | ${mean_d_b:+15,.2f} | {l2w:<12} | {w2l}")
    print("=" * 135)

    out_json = os.path.join(REPORTS_DIR, "exp144_wheat_retention_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "wr_a": _to_native(overall_wr_a),
                "wr_b": _to_native(overall_wr_b),
                "mean_delta_b": _to_native(mean_d_b),
                "l2w": _to_native(l2w),
                "w2l": _to_native(w2l),
            },
            "by_opponent": _to_native(opp_summaries),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP144 Benchmark Results: {out_json}")

if __name__ == "__main__":
    main()
