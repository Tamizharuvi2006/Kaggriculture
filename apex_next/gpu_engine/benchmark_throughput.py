"""
Progressive Throughput Benchmark for RTX 4050 / Multi-Core Batch Simulator.
Tests batch sizes [32, 64, 128, 256], measures execution time, steps per second,
games per second, and verifies mathematical stability across batches.
"""
import sys
import os
import time

# Ensure project root is in sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.gpu_engine.cuda_batch_engine import CudaBatchEngine
from apex_next.gpu_engine.differential_tester import DifferentialTester


def run_benchmark():
    print("==========================================================================")
    print("[BENCHMARK] APEX ACCELERATED ENGINE THROUGHPUT BENCHMARK (RTX 4050 / Vectorized)")
    print("==========================================================================\n")
    
    # 1. Parity & Differential Pre-Check
    print("[1/2] Running Differential Parity Pre-Check...")
    tester = DifferentialTester()
    diff_res = tester.run_golden_comparison(seed=42, steps=100)
    print(f"      Status: {'PASS' if diff_res['passed'] else 'FAIL'}")
    print(f"      Evaluated {diff_res['steps_evaluated']} golden steps in {diff_res['elapsed_ms']}ms.")
    if not diff_res["passed"]:
        print("[FAIL] Parity check failed. Halting benchmark.")
        return

    # 2. Progressive Scaling Benchmark
    print("\n[2/2] Running Progressive Batch Scaling (32 -> 64 -> 128 -> 256 Envs)...")
    print(f"      {'Batch Size':<12} | {'Total Steps':<14} | {'Elapsed (s)':<12} | {'Steps/Sec':<14} | {'Games/Sec':<12}")
    print("      " + "-" * 74)
    
    batch_sizes = [32, 64, 128, 256]
    for b in batch_sizes:
        engine = CudaBatchEngine(batch_size=b, max_steps=720)
        res = engine.run_full_episodes()
        print(f"      {b:<12d} | {res['total_env_steps']:<14d} | {res['elapsed_seconds']:<12.3f} | {res['steps_per_second']:<14.1f} | {res['games_per_second']:<12.2f}")

    print("\n==========================================================================")
    print("[SUCCESS] Benchmark Completed. Vectorized Batch Execution Ready for Mass Screening.")
    print("==========================================================================")


if __name__ == "__main__":
    run_benchmark()
