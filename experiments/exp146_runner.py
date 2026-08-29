"""EXP146 Multi-Process Runner: Evaluates Arms A, B, C, D, E, F across the 5 benchmark suites."""
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
    print("=" * 145)
    print("EXP146: CASH RUNWAY THRESHOLD SWEEP BENCHMARK (600 TOTAL MATCHES ACROSS 5 PROCESSES)")
    print("=" * 145)

    processes = []
    t0 = time.time()

    for idx, bot_file in enumerate(OPPONENTS):
        worker_id = f"opp_{idx}_{bot_file.split('.')[0]}"
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp146_worker.py"), bot_file, worker_id]
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
        part_file = os.path.join(REPORTS_DIR, f"exp146_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
            os.remove(part_file)

    opp_summaries = {}
    print("\n" + "=" * 145)
    print(f"{'Opponent Architecture':<30} | {'Arm A WR':<9} | {'Arm B WR':<9} | {'Arm C WR':<9} | {'Arm D WR':<9} | {'Arm E WR':<9} | {'Arm F WR':<9} | {'Delta F-A ($)'}")
    print("=" * 145)

    total_matches = len(all_data)
    a_wins, b_wins, c_wins, d_wins, e_wins, f_wins = 0, 0, 0, 0, 0, 0
    tot_d_b, tot_d_c, tot_d_d, tot_d_e, tot_d_f = 0.0, 0.0, 0.0, 0.0, 0.0

    for opp_name in OPPONENTS:
        sub_items = [d for d in all_data if d["opponent"] == opp_name]
        n = len(sub_items)
        if n == 0: continue

        n_a = sum(1 for d in sub_items if d["arm_a"]["won"])
        n_b = sum(1 for d in sub_items if d["arm_b"]["won"])
        n_c = sum(1 for d in sub_items if d["arm_c"]["won"])
        n_d = sum(1 for d in sub_items if d["arm_d"]["won"])
        n_e = sum(1 for d in sub_items if d["arm_e"]["won"])
        n_f = sum(1 for d in sub_items if d["arm_f"]["won"])

        d_f = float(np.mean([d["delta_f_vs_a"] for d in sub_items]))

        a_wins += n_a
        b_wins += n_b
        c_wins += n_c
        d_wins += n_d
        e_wins += n_e
        f_wins += n_f

        tot_d_b += sum(d["delta_b_vs_a"] for d in sub_items)
        tot_d_c += sum(d["delta_c_vs_a"] for d in sub_items)
        tot_d_d += sum(d["delta_d_vs_a"] for d in sub_items)
        tot_d_e += sum(d["delta_e_vs_a"] for d in sub_items)
        tot_d_f += sum(d["delta_f_vs_a"] for d in sub_items)

        opp_summaries[opp_name] = {
            "matches": n,
            "wr_a": (n_a / n) * 100, "wr_b": (n_b / n) * 100, "wr_c": (n_c / n) * 100,
            "wr_d": (n_d / n) * 100, "wr_e": (n_e / n) * 100, "wr_f": (n_f / n) * 100,
            "delta_f": d_f,
        }

        print(f"{opp_name:<30} | {(n_a/n)*100:5.1f}%   | {(n_b/n)*100:5.1f}%   | {(n_c/n)*100:5.1f}%   | {(n_d/n)*100:5.1f}%   | {(n_e/n)*100:5.1f}%   | {(n_f/n)*100:5.1f}%   | ${d_f:+13,.2f}")

    print("-" * 145)
    overall_wr_a = (a_wins / total_matches) * 100
    overall_wr_b = (b_wins / total_matches) * 100
    overall_wr_c = (c_wins / total_matches) * 100
    overall_wr_d = (d_wins / total_matches) * 100
    overall_wr_e = (e_wins / total_matches) * 100
    overall_wr_f = (f_wins / total_matches) * 100

    mean_d_b = tot_d_b / total_matches
    mean_d_c = tot_d_c / total_matches
    mean_d_d = tot_d_d / total_matches
    mean_d_e = tot_d_e / total_matches
    mean_d_f = tot_d_f / total_matches

    print(f"{'OVERALL (100 MATCHES / ARM)':<30} | {overall_wr_a:5.1f}%   | {overall_wr_b:5.1f}%   | {overall_wr_c:5.1f}%   | {overall_wr_d:5.1f}%   | {overall_wr_e:5.1f}%   | {overall_wr_f:5.1f}%   | ${mean_d_f:+13,.2f}")
    print("=" * 145)

    out_json = os.path.join(REPORTS_DIR, "exp146_runway_sweep_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "wr_a": _to_native(overall_wr_a), "wr_b": _to_native(overall_wr_b), "wr_c": _to_native(overall_wr_c),
                "wr_d": _to_native(overall_wr_d), "wr_e": _to_native(overall_wr_e), "wr_f": _to_native(overall_wr_f),
                "mean_delta_b": _to_native(mean_d_b), "mean_delta_c": _to_native(mean_d_c), "mean_delta_d": _to_native(mean_d_d),
                "mean_delta_e": _to_native(mean_d_e), "mean_delta_f": _to_native(mean_d_f),
            },
            "by_opponent": _to_native(opp_summaries),
            "all_matches": _to_native(all_data),
        }, f, indent=2)

    print(f"\nSaved Complete EXP146 Sweep Results: {out_json}")

if __name__ == "__main__":
    main()
