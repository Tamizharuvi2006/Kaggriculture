"""EXP124 Multi-Process Runner: Spawns independent chunk workers and aggregates results."""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
import pandas as pd

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def main():
    print("=" * 135)
    print("EXP124: MULTI-PROCESS DAY-30 LABOR BURST BENCHMARK (100 MATCHES ACROSS 5 PROCESSES)")
    print("=" * 135)

    loss_file = os.path.join(REPORTS_DIR, "exp123_loss_cohort_forensics.json")
    with open(loss_file, "r", encoding="utf-8") as f:
        loss_cohort = json.load(f)

    total = len(loss_cohort)
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers for {total} matches...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp124_worker.py"), str(start_idx), str(end_idx)]
        p = subprocess.Popen(cmd)
        processes.append((p, start_idx, end_idx))
        print(f"  Launched worker for chunk [{start_idx}:{end_idx}] (PID: {p.pid})")

    # Wait for all processes to complete
    for p, s, e in processes:
        p.wait()
        if p.returncode != 0:
            print(f"❌ Worker [{s}:{e}] failed with exit code {p.returncode}!")
        else:
            print(f"  ✅ Worker [{s}:{e}] finished successfully.")

    elapsed = time.time() - t0
    print(f"\nAll workers completed in {elapsed:.1f} seconds. Merging results...")

    all_results = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp124_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_results.extend(part_data)
            os.remove(part_file)

    print(f"Total merged results: {len(all_results)}/100 matches.")

    df_comp = pd.DataFrame(all_results)

    # Statistical Synthesis
    print("\n" + "=" * 135)
    print("EXP124: STATISTICAL SYNTHESIS & WIN-CONVERSION RESULTS (100 MATCHES)")
    print("=" * 135)

    loss_to_win = (df_comp["transition"] == "LOSS_TO_WIN").sum()
    loss_to_loss = (df_comp["transition"] == "LOSS_TO_LOSS").sum()
    win_to_loss = (df_comp["transition"] == "WIN_TO_LOSS").sum()
    win_to_win = (df_comp["transition"] == "WIN_TO_WIN").sum()
    net_conversion = loss_to_win - win_to_loss

    print("\n1. MATCH OUTCOME TRANSITION MATRIX:")
    print(f"   - Loss -> Win Conversions  (✅ SUCCESS)   : {loss_to_win:2d} matches ({loss_to_win:4.1f}%)")
    print(f"   - Loss -> Loss Unconverted (❌ NEUTRAL)   : {loss_to_loss:2d} matches ({loss_to_loss:4.1f}%)")
    print(f"   - Win -> Loss Regressions  (🚨 DANGER)    : {win_to_loss:2d} matches ({win_to_loss:4.1f}%)")
    print(f"   - Win -> Win Preserved     (✅ STABLE)    : {win_to_win:2d} matches ({win_to_win:4.1f}%)")
    print(f"   -----------------------------------------------------------------")
    print(f"   - NET CONVERSION SCORE     : {net_conversion:+d} matches ({net_conversion:+4.1f}%)")

    deltas = df_comp["reward_delta"]
    print(f"\n2. TERMINAL REWARD DELTA DISTRIBUTION (Arm B vs Arm A):")
    print(f"   - Mean Reward Delta   : ${deltas.mean():+10,.2f}")
    print(f"   - Median Reward Delta : ${deltas.median():+10,.2f}")
    print(f"   - Min Reward Delta    : ${deltas.min():+10,.2f}")
    print(f"   - Max Reward Delta    : ${deltas.max():+10,.2f}")
    print(f"   - Positive Delta Ratio: {(deltas > 0).sum():2d}/100 matches ({(deltas > 0).mean()*100:4.1f}%)")

    stranded_a = df_comp["arm_a_stranded"].mean()
    stranded_b = df_comp["arm_b_stranded"].mean()
    print(f"\n3. FIELD CLEARING & HARVEST EFFICIENCY:")
    print(f"   - Mean Stranded Crops in Arm A (Control) : {stranded_a:.2f} plots")
    print(f"   - Mean Stranded Crops in Arm B (Burst)   : {stranded_b:.2f} plots (Reduced by {stranded_a - stranded_b:.2f} plots)")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp124_day30_labor_burst_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved Full EXP124 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
