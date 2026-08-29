"""EXP128 Multi-Process Runner: Step-Level Opponent Action-Causality Forensics across 100 Losses."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import numpy as np
import pandas as pd
from collections import Counter

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

def main():
    print("=" * 135)
    print("EXP128: OPPONENT ACTION-CAUSALITY FORENSICS (100 MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    total = len(loss_cohort)
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers for step-level action causality on {total} matches...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp128_action_causality_worker.py"), str(start_idx), str(end_idx)]
        p = subprocess.Popen(cmd)
        processes.append((p, start_idx, end_idx))
        print(f"  Launched worker for chunk [{start_idx}:{end_idx}] (PID: {p.pid})")

    for p, s, e in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{s}:{e}] failed with exit code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{s}:{e}] completed successfully.")

    elapsed = time.time() - t0
    print(f"\nAll causality workers completed in {elapsed:.1f}s. Merging results...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp128_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    print(f"Aggregated {len(all_data)}/100 matches.")

    df = pd.DataFrame(all_data)

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP128: STATISTICAL SYNTHESIS ACROSS 100 LOSS MATCHES")
    print("=" * 135)

    print("\n1. POINT OF NO RETURN (FIRST PERSISTENT DEFICIT TIMING):")
    print(f"   - Mean Step of Persistent Deficit : Step {df['t_persistent_deficit'].mean():.1f} (Day {df['day_persistent_deficit'].mean():.1f})")
    print(f"   - Median Step of Persistent Deficit: Step {df['t_persistent_deficit'].median():.1f} (Day {df['day_persistent_deficit'].median():.1f})")
    print(f"   - Min Step of Persistent Deficit  : Step {df['t_persistent_deficit'].min():.1f} (Day {df['day_persistent_deficit'].min():.1f})")
    print(f"   - Max Step of Persistent Deficit  : Step {df['t_persistent_deficit'].max():.1f} (Day {df['day_persistent_deficit'].max():.1f})")

    # Group by Day Windows
    day_bins = pd.cut(df["day_persistent_deficit"], bins=[0, 5, 10, 15, 20, 25, 31], labels=["Days 1-5", "Days 6-10", "Days 11-15", "Days 16-20", "Days 21-25", "Days 26-30"])
    print("\n2. BREAKDOWN OF POINT OF NO RETURN BY MATCH PHASE:")
    for phase, count in day_bins.value_counts().sort_index().items():
        print(f"   - {phase:<12}: {count:2d} matches ({count/len(df)*100:4.1f}%)")

    # Primary Root Divergence Categories
    print("\n3. PRIMARY ROOT CAUSAL DRIVER OF DEFICIT (RANKED BY FREQUENCY):")
    cat_counts = df["divergence_category"].value_counts()
    print(f"{'Category':<35} | {'Match Count':<12} | {'Percentage':<12} | {'Mean Final Deficit':<20} | {'Mean Day Diverged'}")
    print("-" * 115)
    for cat, count in cat_counts.items():
        sub_c = df[df["divergence_category"] == cat]
        mean_def = sub_c["final_delta"].mean()
        mean_d = sub_c["day_persistent_deficit"].mean()
        print(f"{cat:<35} | {count:2d} matches   | {count/len(df)*100:4.1f}%       | ${mean_def:+12,.2f}        | Day {mean_d:4.1f}")

    print("\n4. MARKET PRICE CONDITIONS AT POINT OF NO RETURN:")
    print(f"   - Mean Milk Price at Divergence      : ${df['milk_price_at_point_of_no_return'].mean():6.2f}")
    print(f"   - Mean Wool Price at Divergence      : ${df['wool_price_at_point_of_no_return'].mean():6.2f}")
    print(f"   - Mean Strawberry Price at Divergence: ${df['straw_price_at_point_of_no_return'].mean():6.2f}")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp128_action_causality_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "mean_step_diverged": _to_native(df["t_persistent_deficit"].mean()),
                "median_step_diverged": _to_native(df["t_persistent_deficit"].median()),
                "categories": _to_native(cat_counts.to_dict()),
            },
            "matches": _to_native(all_data),
        }, f, indent=2)
    print(f"\nSaved Full EXP128 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
