"""EXP130 Multi-Process Runner: Evaluates 4 Arms across 100 Loss Matches."""
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

    milk_trigs = df_results[arm_col].apply(lambda x: x["milk_triggers"])
    straw_trigs = df_results[arm_col].apply(lambda x: x["straw_triggers"])
    active_count = ((milk_trigs > 0) | (straw_trigs > 0)).sum()

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
        "active_matches": active_count,
        "mean_milk_triggers": milk_trigs.mean(),
        "mean_straw_triggers": straw_trigs.mean(),
    }

def main():
    print("=" * 135)
    print("EXP130: SEQUENTIAL ENDGAME DEFENSE FACTORIZATION (100 MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    total = len(loss_cohort)
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers for 4-arm evaluation on {total} matches...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp130_worker.py"), str(start_idx), str(end_idx)]
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
    print(f"\nAll 4-arm workers completed in {elapsed:.1f}s. Merging results...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp130_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    print(f"Aggregated {len(all_data)}/100 matches.")

    df_res = pd.DataFrame(all_data)

    stats_b = analyze_arm(df_res, "Arm B: Milk Collapse Defense", "arm_b")
    stats_c = analyze_arm(df_res, "Arm C: Strawberry Collapse Defense", "arm_c")
    stats_d = analyze_arm(df_res, "Arm D: Combined (Milk + Strawberry)", "arm_d")

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP130: 4-ARM WIN-CONVERSION & INTERACTION SYNTHESIS (100 MATCHES)")
    print("=" * 135)

    print(f"\n{'Arm / Policy':<38} | {'Loss->Win':<10} | {'Win->Loss':<10} | {'Net Conv':<10} | {'Mean Delta ($)':<15} | {'Median Delta':<14} | {'Min Delta':<12} | {'Max Delta':<12} | {'Pos Ratio'}")
    print("-" * 135)
    for st in [stats_b, stats_c, stats_d]:
        print(f"{st['arm_name']:<38} | {st['loss_to_win']:2d} matches  | {st['win_to_loss']:2d} matches  | {st['net_conversion']:+3d} matches | ${st['mean_delta']:+12,.2f} | ${st['median_delta']:+11,.2f} | ${st['min_delta']:+10,.2f} | ${st['max_delta']:+10,.2f} | {st['positive_delta_pct']:4.1f}%")

    print("\n" + "-" * 135)
    print("TRIGGER FREQUENCY & INTERACTION METRICS:")
    for st in [stats_b, stats_c, stats_d]:
        print(f"  {st['arm_name']}:")
        print(f"     - Trigger Frequency      : {st['active_matches']:2d} / 100 matches ({st['active_matches']:4.1f}%)")
        print(f"     - Mean Milk Triggers     : {st['mean_milk_triggers']:.1f} events")
        print(f"     - Mean Straw Triggers    : {st['mean_straw_triggers']:.1f} events")

    # Check for Interaction synergy (D vs B + C)
    deltas_b = df_res["arm_b"].apply(lambda x: x["reward"]) - df_res["arm_a"].apply(lambda x: x["reward"])
    deltas_c = df_res["arm_c"].apply(lambda x: x["reward"]) - df_res["arm_a"].apply(lambda x: x["reward"])
    deltas_d = df_res["arm_d"].apply(lambda x: x["reward"]) - df_res["arm_a"].apply(lambda x: x["reward"])

    superadditive_count = (deltas_d > (deltas_b + deltas_c)).sum()
    print(f"\nINTERACTION SYNERGY ANALYSIS:")
    print(f"  - Matches where Combined (D) > (B + C) (Super-additive synergy) : {superadditive_count} / 100 matches")
    print(f"  - Mean Delta Difference (D - (B + C))                          : ${(deltas_d - (deltas_b + deltas_c)).mean():+,.2f}")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp130_endgame_factorization_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "summary": [_to_native(st) for st in [stats_b, stats_c, stats_d]],
            "matches": _to_native(all_data),
        }, f, indent=2)
    print(f"\nSaved Full EXP130 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
