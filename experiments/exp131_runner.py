"""EXP131 Multi-Process Runner: Evaluates Control D.1 vs Candidate D.2 on 100 Fresh Unseen Matches."""
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

def main():
    print("=" * 135)
    print("EXP131: FRESH OUT-OF-SAMPLE GENERALIZATION VALIDATION (100 FRESH SEEDS ACROSS 5 PROCESSES)")
    print("=" * 135)

    total = 100
    chunk_size = 20
    chunks = [(i, min(i + chunk_size, total)) for i in range(0, total, chunk_size)]

    print(f"Spawning {len(chunks)} independent python workers on {total} fresh unseen seeds [20001..20100]...")
    processes = []
    t0 = time.time()

    for start_idx, end_idx in chunks:
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp131_worker.py"), str(start_idx), str(end_idx)]
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
    print(f"\nAll out-of-sample workers completed in {elapsed:.1f}s. Merging results...")

    all_data = []
    for start_idx, end_idx in chunks:
        part_file = os.path.join(REPORTS_DIR, f"exp131_part_{start_idx}_{end_idx}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                part_data = json.load(f)
                all_data.extend(part_data)
            os.remove(part_file)

    print(f"Aggregated {len(all_data)}/100 matches.")

    df = pd.DataFrame(all_data)

    d1_wins = df["d1_won"].sum()
    cand_wins = df["cand_won"].sum()
    total_matches = len(df)

    d1_win_rate = (d1_wins / total_matches) * 100
    cand_win_rate = (cand_wins / total_matches) * 100

    loss_to_win = ((~df["d1_won"]) & df["cand_won"]).sum()
    loss_to_loss = ((~df["d1_won"]) & (~df["cand_won"])).sum()
    win_to_loss = (df["d1_won"] & (~df["cand_won"])).sum()
    win_to_win = (df["d1_won"] & df["cand_won"]).sum()
    net_conversion = loss_to_win - win_to_loss

    deltas = df["reward_delta"]
    mean_delta = deltas.mean()
    median_delta = deltas.median()
    min_delta = deltas.min()
    max_delta = deltas.max()
    pos_pct = (deltas > 0).mean() * 100

    milk_active = (df["milk_triggers"] > 0).sum()
    straw_active = (df["straw_triggers"] > 0).sum()
    hires_active = (df["hires_done"] > 0).sum()

    print("\n" + "=" * 135)
    print("EXP131: FRESH GENERALIZATION BENCHMARK SUMMARY (100 UNSEEN MATCHES)")
    print("=" * 135)

    print(f"\n1. WIN RATE & TRANSITION MATRIX:")
    print(f"   - D.1 Control Win Rate          : {d1_wins:2d} / {total_matches} ({d1_win_rate:5.1f}%)")
    print(f"   - Candidate D.2 Win Rate        : {cand_wins:2d} / {total_matches} ({cand_win_rate:5.1f}%)")
    print(f"   - Net Win Rate Increase         : {cand_win_rate - d1_win_rate:+5.1f}% ({cand_wins - d1_wins:+2d} net wins)")
    print(f"   - Loss -> Win Conversions       : {loss_to_win:2d} matches ({loss_to_win/total_matches*100:4.1f}%)")
    print(f"   - Win -> Loss Regressions       : {win_to_loss:2d} matches ({win_to_loss/total_matches*100:4.1f}%) (Strict No-Regression Gate)")
    print(f"   - Net Win Conversion Score      : {net_conversion:+2d} matches")

    print(f"\n2. ECONOMIC DELTA & ALPHA DISTRIBUTION:")
    print(f"   - Mean Terminal Reward Delta    : ${mean_delta:+12,.2f}")
    print(f"   - Median Terminal Reward Delta  : ${median_delta:+12,.2f}")
    print(f"   - Minimum Delta (Max Drawdown)  : ${min_delta:+12,.2f}")
    print(f"   - Maximum Delta (Max Gain)      : ${max_delta:+12,.2f}")
    print(f"   - Matches with Positive Alpha   : {pos_pct:5.1f}% ({int(pos_pct*total_matches/100)} / {total_matches} matches)")

    print(f"\n3. ADAPTIVE TRIGGER EXECUTION METRICS:")
    print(f"   - Milk Collapse Defense Active  : {milk_active:2d} / {total_matches} matches ({milk_active/total_matches*100:4.1f}%)")
    print(f"   - Strawberry Defense Active     : {straw_active:2d} / {total_matches} matches ({straw_active/total_matches*100:4.1f}%)")
    print(f"   - Day-30 Labor Burst Active     : {hires_active:2d} / {total_matches} matches ({hires_active/total_matches*100:4.1f}%)")

    # Save JSON Report
    out_json = os.path.join(REPORTS_DIR, "exp131_fresh_validation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "d1_wins": _to_native(d1_wins),
                "cand_wins": _to_native(cand_wins),
                "d1_win_rate": _to_native(d1_win_rate),
                "cand_win_rate": _to_native(cand_win_rate),
                "loss_to_win": _to_native(loss_to_win),
                "win_to_loss": _to_native(win_to_loss),
                "net_conversion": _to_native(net_conversion),
                "mean_delta": _to_native(mean_delta),
                "median_delta": _to_native(median_delta),
                "min_delta": _to_native(min_delta),
                "max_delta": _to_native(max_delta),
                "pos_pct": _to_native(pos_pct),
            },
            "matches": _to_native(all_data),
        }, f, indent=2)
    print(f"\nSaved Full EXP131 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
