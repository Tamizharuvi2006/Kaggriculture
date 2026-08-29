"""EXP150 Multi-Process Mirror Detector Runner."""
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
    print("EXP150: SATURATED MIRROR-REGIME DETECTOR MINING (10 ARCHETYPES / 200 MATCHES)")
    print("=" * 145)

    all_keys = list(POPULATION_SUITE.keys())
    chunks = [all_keys[i:i+2] for i in range(0, len(all_keys), 2)]

    processes = []
    t0 = time.time()

    for idx, chunk in enumerate(chunks):
        worker_id = f"worker_{idx}"
        chunk_str = ",".join(chunk)
        cmd = [sys.executable, os.path.join(BASE_DIR, "experiments", "exp150_worker.py"), chunk_str, worker_id]
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
    print(f"\nAll workers finished in {elapsed:.1f}s. Aggregating trajectory profiles...")

    all_matches = []
    for idx in range(len(chunks)):
        worker_id = f"worker_{idx}"
        part_file = os.path.join(REPORTS_DIR, f"exp150_part_{worker_id}.json")
        if os.path.exists(part_file):
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_matches.extend(data)
            os.remove(part_file)

    mirror_matches = [m for m in all_matches if m["is_mirror"]]
    non_mirror_matches = [m for m in all_matches if not m["is_mirror"]]
    print(f"Audited {len(all_matches)} total matches ({len(mirror_matches)} mirror matches, {len(non_mirror_matches)} non-mirror matches).\n")

    # 1. Compare Observable Trajectories: Mirror vs Non-Mirror Archetypes
    print("=" * 145)
    print("1. PUBLIC OBSERVABLE SIGNATURE COMPARISON (MIRROR VS NON-MIRROR ARCHETYPES):")
    print("=" * 145)
    print(f"{'Checkpoint Step':<18} | {'Mirror Straw':<15} | {'Non-Mirror Straw':<18} | {'Mirror Cows':<15} | {'Non-Mirror Cows':<18} | {'Mirror Carrots':<15} | {'Non-Mirror Carrots'}")
    print("-" * 145)

    checkpoints = [72, 96, 120, 144, 168, 192, 216, 240]
    for step in checkpoints:
        k = f"step_{step}"
        m_straw = np.mean([m["snapshots"][k]["opp_straw"] for m in mirror_matches])
        nm_straw = np.mean([m["snapshots"][k]["opp_straw"] for m in non_mirror_matches])
        m_cows = np.mean([m["snapshots"][k]["opp_cows"] for m in mirror_matches])
        nm_cows = np.mean([m["snapshots"][k]["opp_cows"] for m in non_mirror_matches])
        m_carrots = np.mean([m["snapshots"][k]["opp_carrots"] for m in mirror_matches])
        nm_carrots = np.mean([m["snapshots"][k]["opp_carrots"] for m in non_mirror_matches])

        print(f"Step {step:<3} (Day {step//24:02d}){'':<4} | {m_straw:5.2f} tiles{'':<5} | {nm_straw:5.2f} tiles{'':<8} | {m_cows:5.2f} cows{'':<6} | {nm_cows:5.2f} cows{'':<9} | {m_carrots:5.2f} tiles{'':<5} | {nm_carrots:5.2f} tiles")

    # 2. Evaluate Candidate Detectors
    print("\n" + "=" * 145)
    print("2. CANDIDATE DETECTOR ACCURACY MATRIX (PRECISION, RECALL, FALSE POSITIVE RATE):")
    print("=" * 145)
    print(f"{'Detector Rule':<55} | {'Earliest Step':<15} | {'True Positives':<16} | {'False Positives':<16} | {'Accuracy':<10} | {'FPR'}")
    print("-" * 145)

    candidate_rules = [
        # Candidate 1: Day 3/Step 72 (Straw >= 1 and Carrots == 0 and Cows == 0)
        ("Step 72: Straw >= 1 and Carrots == 0", 72,
         lambda snap: snap["step_72"]["opp_straw"] >= 1 and snap["step_72"]["opp_carrots"] == 0),

        # Candidate 2: Day 5/Step 120 (Straw >= 4 and Carrots == 0 and Sheep == 0)
        ("Step 120: Straw >= 4 and Carrots == 0 and Sheep == 0", 120,
         lambda snap: snap["step_120"]["opp_straw"] >= 4 and snap["step_120"]["opp_carrots"] == 0 and snap["step_120"]["opp_sheep"] == 0),

        # Candidate 3: Day 7/Step 168 (Straw >= 6 and Carrots == 0 and Cows <= 5 and Sheep == 0)
        ("Step 168: Straw >= 6 and Carrots == 0 and Cows <= 5", 168,
         lambda snap: snap["step_168"]["opp_straw"] >= 6 and snap["step_168"]["opp_carrots"] == 0 and snap["step_168"]["opp_cows"] <= 5 and snap["step_168"]["opp_sheep"] == 0),

        # Candidate 4: Day 9/Step 216 (Straw >= 14 and Carrots == 0 and Cows in [4..8])
        ("Step 216: Straw >= 14 and Carrots == 0 and Cows <= 8", 216,
         lambda snap: snap["step_216"]["opp_straw"] >= 14 and snap["step_216"]["opp_carrots"] == 0 and snap["step_216"]["opp_cows"] <= 8 and snap["step_216"]["opp_sheep"] == 0),
    ]

    detector_results = []
    for desc, step_trig, fn in candidate_rules:
        tp = sum(1 for m in mirror_matches if fn(m["snapshots"]))
        fn_count = len(mirror_matches) - tp
        fp = sum(1 for m in non_mirror_matches if fn(m["snapshots"]))
        tn = len(non_mirror_matches) - fp

        accuracy = (tp + tn) / len(all_matches) * 100
        fpr = (fp / len(non_mirror_matches)) * 100
        tpr = (tp / len(mirror_matches)) * 100

        detector_results.append({
            "description": desc,
            "step": step_trig,
            "tp": tp, "fp": fp, "fn": fn_count, "tn": tn,
            "accuracy": accuracy, "fpr": fpr, "tpr": tpr,
        })

        print(f"{desc:<55} | Step {step_trig:<9} | {tp}/{len(mirror_matches)} ({tpr:5.1f}%){'':<4} | {fp}/{len(non_mirror_matches)} ({fpr:5.1f}%){'':<4} | {accuracy:5.1f}%    | {fpr:5.1f}%")

    out_json = os.path.join(REPORTS_DIR, "exp150_mirror_detector_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_matches": len(all_matches),
            "mirror_matches": len(mirror_matches),
            "non_mirror_matches": len(non_mirror_matches),
            "detector_candidates": _to_native(detector_results),
            "all_matches": _to_native(all_matches),
        }, f, indent=2)

    print(f"\nSaved Complete EXP150 Detector Mining Results: {out_json}")
    print("=" * 145)

if __name__ == "__main__":
    main()
