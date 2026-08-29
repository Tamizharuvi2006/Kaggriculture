"""EXP136 Multi-Process Runner: Evaluates Step-696 Bug Fix across 100 Losses & 100 Fresh Seeds."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd

# Ensure UTF-8 on Windows
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

def run_cohort(cohort_type: str, total: int = 100):
    print(f"\n" + "=" * 135)
    print(f"RUNNING EXP136 BENCHMARK ON COHORT: {cohort_type.upper()} ({total} MATCHES)")
    print("=" * 135)

    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp136_worker.py"), cohort_type, str(start_idx), str(end_idx)]
        p = subprocess.Popen(cmd)
        processes.append((p, start_idx, end_idx))
        print(f"  Launched worker for chunk [{start_idx}:{end_idx}] (PID: {p.pid})")

    for p, s, e in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{cohort_type}:{s}:{e}] failed with exit code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{cohort_type}:{s}:{e}] completed successfully.")

    elapsed = time.time() - t0
    print(f"Completed {cohort_type} in {elapsed:.1f}s. Aggregating results...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp136_{cohort_type}_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    df = pd.DataFrame(all_data)

    l2w = ((~df["ctrl_won"]) & df["fix_won"]).sum()
    w2l = (df["ctrl_won"] & (~df["fix_won"])).sum()
    net_conv = l2w - w2l

    ctrl_wins = df["ctrl_won"].sum()
    fix_wins = df["fix_won"].sum()

    deltas = df["delta"]
    mean_delta = deltas.mean()
    median_delta = deltas.median()
    min_delta = deltas.min()
    max_delta = deltas.max()
    pos_pct = (deltas > 0).mean() * 100

    print(f"\n--- {cohort_type.upper()} SUMMARY ({total} MATCHES) ---")
    print(f"  - Control D.1 Win Rate         : {ctrl_wins:2d} / {total} ({ctrl_wins/total*100:5.1f}%)")
    print(f"  - Bug-Fixed D.1 Win Rate       : {fix_wins:2d} / {total} ({fix_wins/total*100:5.1f}%)")
    print(f"  - Net Win Rate Increase        : {fix_wins - ctrl_wins:+2d} matches ({(fix_wins - ctrl_wins)/total*100:+5.1f}%)")
    print(f"  - Loss -> Win Conversions      : {l2w:2d} matches ({l2w/total*100:5.1f}%)")
    print(f"  - Win -> Loss Regressions      : {w2l:2d} matches ({w2l/total*100:5.1f}%)")
    print(f"  - Net Conversion Score         : {net_conv:+2d} matches")
    print(f"  - Mean Reward Delta ($)        : ${mean_delta:+12,.2f}")
    print(f"  - Median Reward Delta ($)      : ${median_delta:+12,.2f}")
    print(f"  - Min / Max Delta ($)          : ${min_delta:+10,.2f} / ${max_delta:+10,.2f}")
    print(f"  - Positive Delta Ratio         : {pos_pct:5.1f}% ({int(pos_pct*total/100)} / {total} matches)")

    return {
        "cohort_type": cohort_type,
        "ctrl_wins": _to_native(ctrl_wins),
        "fix_wins": _to_native(fix_wins),
        "l2w": _to_native(l2w),
        "w2l": _to_native(w2l),
        "net_conv": _to_native(net_conv),
        "mean_delta": _to_native(mean_delta),
        "median_delta": _to_native(median_delta),
        "min_delta": _to_native(min_delta),
        "max_delta": _to_native(max_delta),
        "pos_pct": _to_native(pos_pct),
        "matches": _to_native(all_data),
    }

def main():
    print("=" * 135)
    print("EXP136: STEP-696 BUG-FIX ISOLATION BENCHMARK (200 TOTAL MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    loss_summary = run_cohort("loss", total=100)
    fresh_summary = run_cohort("fresh", total=100)

    out_json = os.path.join(REPORTS_DIR, "exp136_step696_bugfix_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "historical_loss_cohort": loss_summary,
            "fresh_unseen_cohort": fresh_summary,
        }, f, indent=2)
    print(f"\n" + "=" * 135)
    print(f"Saved Complete EXP136 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
