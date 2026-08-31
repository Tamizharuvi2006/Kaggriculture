"""FastSim Phase 5: 100-Case Differential Validation Suite.

Executes 100 test cases comparing the Official Python Oracle against FastSim.
Requires 100% bit-exact equivalence on all checkpoints and final rewards.
"""
import os
import sys
import json
import time
import subprocess
from typing import List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.run_official_case import run_official_case
from tools.diff_case import compare_traces

def build_test_cases() -> List[Tuple[int, int, str, str]]:
    cases = []
    # 1. 60 random seeds
    for s in range(1001, 1061):
        seat = s % 2
        cases.append((s, seat, "starter", "pass"))

    # 2. 20 historical project seeds
    for s in range(91001, 91021):
        seat = (s - 91001) % 2
        cases.append((s, seat, "starter", "pass"))

    # 3. 10 mirror cases (starter vs starter)
    for s in range(2001, 2011):
        cases.append((s, 0, "starter", "starter"))

    # 4. 10 edge case seeds
    edge_seeds = [1, 2, 3, 4, 5, 42, 999, 12345, 99999, 777777]
    for i, s in enumerate(edge_seeds):
        cases.append((s, i % 2, "starter", "pass"))

    assert len(cases) == 100, f"Expected 100 cases, got {len(cases)}"
    return cases

def run_100_differential_suite(fastsim_exe: str):
    cases = build_test_cases()
    temp_dir = os.path.join(BASE_DIR, "fastsim", "results", "diff_100")
    os.makedirs(temp_dir, exist_ok=True)

    print("=" * 100)
    print("FASTSIM PHASE 5: 100-CASE DIFFERENTIAL VALIDATION SUITE")
    print("=" * 100)
    print(f"Total Test Cases : {len(cases)} (60 Random, 20 Historical, 10 Mirror, 10 Edge Cases)")
    print(f"FastSim Binary   : {fastsim_exe}")
    print("-" * 100)

    passed = 0
    failed = 0
    t0 = time.time()

    for idx, (seed, seat, hero, opp) in enumerate(cases, 1):
        case_id = f"case_{idx:03d}_s{seed}_seat{seat}_{hero}_vs_{opp}"
        off_json = os.path.join(temp_dir, f"{case_id}_official.json")
        rust_json = os.path.join(temp_dir, f"{case_id}_rust.json")

        # 1. Run Official Python
        run_official_case(seed, seat, hero, opp, off_json)

        # 2. Run FastSim Rust
        cmd = [
            fastsim_exe,
            "--seed", str(seed),
            "--seat", str(seat),
            "--hero", hero,
            "--opponent", opp,
            "--output", rust_json
        ]
        ret = subprocess.run(cmd, capture_output=True, text=True)
        if ret.returncode != 0:
            print(f"\n[ERROR] Case {idx:3d} FastSim crashed!")
            print(f"Stderr: {ret.stderr}")
            failed += 1
            break

        # 3. Diff Traces
        is_exact = compare_traces(off_json, rust_json, verbose=False)
        if is_exact:
            passed += 1
            print(f"  [Case {idx:3d}/100] PASS | Seed: {seed:6d} | Seat: {seat} | {hero} vs {opp}")
        else:
            failed += 1
            print(f"\n[FAIL] Case {idx:3d} Diverged!")
            compare_traces(off_json, rust_json, verbose=True)
            print("\nDifferential Validation STOPPED on first divergence.")
            break

    elapsed = time.time() - t0
    print("=" * 100)
    print(f"DIFFERENTIAL SUITE SUMMARY: {passed}/100 PASSED ({passed}%) | {failed} FAILED | Elapsed: {elapsed:.2f}s")
    print("=" * 100)

    if failed == 0 and passed == 100:
        print(">>> 100% BIT-EXACT DIFFERENTIAL VALIDATION PASSED! ALL CHECKS VERIFIED! <<<")
        return True
    return False

def main():
    fastsim_exe = os.path.join(BASE_DIR, "fastsim", "target", "release", "fastsim.exe")
    if not os.path.exists(fastsim_exe):
        fastsim_exe = os.path.join(BASE_DIR, "fastsim", "target", "debug", "fastsim.exe")

    if not os.path.exists(fastsim_exe):
        print(f"Error: FastSim executable not found at {fastsim_exe}. Please build it first.")
        sys.exit(1)

    ok = run_100_differential_suite(fastsim_exe)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
