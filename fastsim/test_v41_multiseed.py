import subprocess
import sys
import os

SEEDS = [1000, 1001, 1002, 1003, 1005, 1010, 1020, 1050, 2000, 9999]
SEATS = [0, 1]

total_tests = 0
passed_tests = 0

print("=" * 70)
print("RUNNING V4.1 POLICY MULTI-SEED DIFFERENTIAL VALIDATION SUITE")
print("=" * 70)

for seed in SEEDS:
    for seat in SEATS:
        total_tests += 1
        off_path = f"D:/kaggriculture/fastsim/results/v41_off_{seed}_s{seat}.json"
        rust_path = f"D:/kaggriculture/fastsim/results/v41_rust_{seed}_s{seat}.json"
        
        # 1. Run official
        p_off = subprocess.run([
            "python", "D:/kaggriculture/tools/run_official_case.py",
            "--seed", str(seed),
            "--seat", str(seat),
            "--hero", "v41",
            "--opponent", "pass",
            "--output", off_path
        ], capture_output=True, text=True)
        
        if p_off.returncode != 0:
            print(f"[{total_tests:2d}] Seed {seed:4d} Seat {seat} -> Official Crashed!")
            print(p_off.stderr)
            continue
            
        # 2. Run FastSim
        p_rust = subprocess.run([
            "D:/kaggriculture/fastsim/target/release/fastsim.exe",
            "--seed", str(seed),
            "--seat", str(seat),
            "--hero", "v41",
            "--opponent", "pass",
            "--output", rust_path
        ], capture_output=True, text=True)
        
        if p_rust.returncode != 0:
            print(f"[{total_tests:2d}] Seed {seed:4d} Seat {seat} -> FastSim Crashed!")
            print(p_rust.stderr)
            continue
            
        # 3. Diff
        p_diff = subprocess.run([
            "python", "D:/kaggriculture/tools/diff_case.py",
            "--official", off_path,
            "--rust", rust_path
        ], capture_output=True, text=True)
        
        if p_diff.returncode == 0 and "MATCH PASSED 100% BIT-EXACT!" in p_diff.stdout:
            passed_tests += 1
            print(f"[{total_tests:2d}] Seed {seed:4d} Seat {seat} -> PASSED (100% Bit-Exact)")
        else:
            print(f"[{total_tests:2d}] Seed {seed:4d} Seat {seat} -> FAILED")
            print(p_diff.stdout)

print("=" * 70)
print(f"SUITE COMPLETE: {passed_tests} / {total_tests} PASSED ({passed_tests/total_tests*100:.1f}%)")
print("=" * 70)

# Clean up temp traces
for seed in SEEDS:
    for seat in SEATS:
        for p in [f"D:/kaggriculture/fastsim/results/v41_off_{seed}_s{seat}.json", f"D:/kaggriculture/fastsim/results/v41_rust_{seed}_s{seat}.json"]:
            if os.path.exists(p):
                os.remove(p)
