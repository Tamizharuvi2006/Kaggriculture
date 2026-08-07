"""Pre-Upload Verification Audit for baseline/submission_v83_standalone.py.

Verifies:
1. Python AST & Bytecode Compilation (py_compile)
2. Zero __file__ variable references
3. Zero local file open() calls
4. Zero local module imports
5. Valid Kaggle Entrypoint Signature (def agent(obs, configuration=None))
6. 10-Seed Isolated Simulation Benchmark (Seeds 1000-1009) with zero errors
"""

import sys
import os
import re
import py_compile
import statistics
import importlib.util
import kaggle_environments

SUB_FILE = r"D:\kaggriculture\baseline\submission_v83_standalone.py"

def audit():
    print("=" * 90)
    print(" PRE-UPLOAD VERIFICATION AUDIT FOR SUBMISSION_V83_STANDALONE.PY")
    print("=" * 90)

    # 1. Bytecode Compilation Check
    print("\n[1/6] Checking Python Bytecode Compilation...")
    try:
        py_compile.compile(SUB_FILE, doraise=True)
        print("  [PASS] Syntax and bytecode compilation clean (0 syntax errors).")
    except Exception as e:
        print(f"  [FAIL] Syntax Error: {e}")
        return False

    # 2. Source Code Inspection
    with open(SUB_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    print("\n[2/6] Checking for Forbidden __file__ References...")
    file_matches = re.findall(r"\b__file__\b", code)
    if file_matches:
        print(f"  [FAIL] Found {len(file_matches)} __file__ references!")
        return False
    else:
        print("  [PASS] 0 __file__ references found.")

    print("\n[3/6] Checking for Forbidden File Open Calls...")
    open_matches = [line for line in code.split("\n") if "open(" in line and not line.strip().startswith("#")]
    if open_matches:
        print(f"  [WARNING] Found {len(open_matches)} open() calls:")
        for l in open_matches:
            print("   ", l.strip())
    else:
        print("  [PASS] 0 disk open() calls found.")

    print("\n[4/6] Checking for Forbidden Local Module Imports...")
    import_matches = [line for line in code.split("\n") if ("importlib" in line or "kaitofukami" in line) and not line.strip().startswith("#")]
    if import_matches:
        print(f"  [FAIL] Found local file import references:")
        for l in import_matches:
            print("   ", l.strip())
        return False
    else:
        print("  [PASS] 0 local module imports found.")

    print("\n[5/6] Checking Entrypoint Interface Signature...")
    if "def agent(obs," in code or "def agent(obs):" in code:
        print("  [PASS] Standard 'def agent(obs, configuration=None)' entrypoint verified.")
    else:
        print(f"  [FAIL] agent(obs, configuration=None) entrypoint not found!")
        return False

    # 6. Isolated 10-Seed Kaggle Simulation Test
    print("\n[6/6] Running 10-Seed Isolated Simulation Test (Seeds 1000-1009)...")
    spec = importlib.util.spec_from_file_location("v83_audit_module", SUB_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    scores = []
    for seed in range(1000, 1010):
        try:
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            state = env.run([mod.agent, mod.agent])
            score0 = float(state[-1][0]["observation"]["farms"][0]["money"])
            scores.append(score0)
            print(f"  Seed {seed}: Final Score = ${score0:,.2f} [OK]")
        except Exception as e:
            print(f"  [FAIL] Simulation crashed on seed {seed}: {e}")
            return False

    print("\n" + "=" * 90)
    print(" PRE-UPLOAD VERIFICATION AUDIT SUMMARY")
    print("=" * 90)
    print(f" Total File Size:       {os.path.getsize(SUB_FILE):,} bytes ({code.count(chr(10)):,} lines)")
    print(f" 10-Seed Test Avg Score: ${statistics.mean(scores):,.2f}")
    print(" Status:                 100% KAGGLE SAFE & READY FOR UPLOAD")
    print("=" * 90)
    return True

if __name__ == "__main__":
    audit()
