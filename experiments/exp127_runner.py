"""EXP127 Multi-Process Runner: Evaluates 3 Arms across 100 Loss Matches."""
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

def analyze_arm(df_results, arm_name: str, arm_col: str):
    a_won = df_results["arm_a"].apply(lambda x: x["won"])
    arm_won = df_results[arm_col].apply(lambda x: x["won"])

    a_rew = df_results["arm_a"].apply(lambda x: x["reward"])
    arm_rew = df_results[arm_col].apply(lambda x: x["reward"])
    deltas = arm_rew - a_rew

    loss_to_win = ((~a_won) & arm_won).sum()
    loss_to_loss = ((~a_won) & (~arm_won)).sum()
    win_to_loss = (a_won & (~arm_won)).sum()
    win_to_win = (a_won & arm_won).sum()
    net_conversion = loss_to_win - win_to_loss

    pivoted_count = df_results[arm_col].apply(lambda x: x["pivoted"]).sum()
    trigger_steps = [x["trigger_step"] for x in df_results[arm_col] if x["trigger_step"] is not None]

    return {
        "arm_name": arm_name,
        "loss_to_win": loss_to_win,
        "loss_to_loss": loss_to_loss,
        "win_to_loss": win_to_loss,
        "win_to_win": win_to_win,
        "net_conversion": net_conversion,
        "mean_delta": deltas.mean(),
        "median_delta": deltas.median(),
        "min_delta": deltas.min(),
        "max_delta": deltas.max(),
        "positive_delta_pct": (deltas > 0).mean() * 100,
        "pivoted_matches": pivoted_count,
        "mean_trigger_step": np.mean(trigger_steps) if trigger_steps else None,
    }

def main():
    print("=" * 135)
    print("EXP127: SINGLE-SLOT ADAPTIVE LIVESTOCK RESPONSE (100 MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    total = len(loss_cohort)
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers for 3-arm evaluation on {total} matches...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp127_worker.py"), str(start_idx), str(end_idx)]
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
    print(f"\nAll 3-arm workers completed in {elapsed:.1f}s. Merging results...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp127_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    print(f"Aggregated {len(all_data)}/100 matches.")

    df_res = pd.DataFrame(all_data)

    stats_b = analyze_arm(df_res, "Arm B: Price-Only (Wool>=195, Milk<=130)", "arm_b")
    stats_c = analyze_arm(df_res, "Arm C: Full Opponent (OppSheep>=1 + Price)", "arm_c")

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP127: 3-ARM WIN-CONVERSION & LIVESTOCK ADAPTATION RESULTS (100 MATCHES)")
    print("=" * 135)

    print(f"\n{'Arm / Policy':<40} | {'Loss->Win':<10} | {'Win->Loss':<10} | {'Net Conv':<10} | {'Mean Delta ($)':<15} | {'Median Delta':<14} | {'Min Delta':<12} | {'Max Delta':<12} | {'Pos Ratio'}")
    print("-" * 135)
    for st in [stats_b, stats_c]:
        print(f"{st['arm_name']:<40} | {st['loss_to_win']:2d} matches  | {st['win_to_loss']:2d} matches  | {st['net_conversion']:+3d} matches | ${st['mean_delta']:+12,.2f} | ${st['median_delta']:+11,.2f} | ${st['min_delta']:+10,.2f} | ${st['max_delta']:+10,.2f} | {st['positive_delta_pct']:4.1f}%")

    print("\n" + "-" * 135)
    print("TRIGGER FREQUENCY & STEP TIMING:")
    for st in [stats_b, stats_c]:
        step_str = f"Step {st['mean_trigger_step']:.1f}" if st['mean_trigger_step'] is not None else "None"
        print(f"  {st['arm_name']}:")
        print(f"     - Trigger Frequency      : {st['pivoted_matches']:2d} / 100 matches ({st['pivoted_matches']:4.1f}%)")
        print(f"     - Mean Trigger Step      : {step_str}")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp127_livestock_adaptation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "summary": [_to_native(st) for st in [stats_b, stats_c]],
            "matches": _to_native(all_data),
        }, f, indent=2)
    print(f"\nSaved Full EXP127 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
