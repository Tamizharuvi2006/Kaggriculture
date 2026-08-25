"""
Stage 2: Comprehensive Hardware Profiling & Batch Scaling Benchmark
Profiles RTX 4050 / multi-core vectorized throughput across batch sizes:
[32, 64, 128, 256, 512] environments.
Measures games/sec, steps/sec, elapsed time, and determines the optimal sweet spot.
"""
import os
import sys
import time
import json
import psutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.gpu_engine.cuda_batch_engine import CudaBatchEngine


def run_stage2_benchmark(batch_sizes=[32, 64, 128, 256, 512], max_steps=720):
    print("==========================================================================")
    print("[STAGE 2] HARDWARE PROFILING & BATCH SCALING BENCHMARK (RTX 4050)")
    print("==========================================================================\n")
    
    process = psutil.Process(os.getpid())
    results = []
    
    print(f"{'Batch':<8} | {'Total Steps':<14} | {'Elapsed (s)':<12} | {'Steps/Sec':<14} | {'Games/Sec':<12} | {'RAM (MB)':<10}")
    print("-" * 80)
    
    for b in batch_sizes:
        # Warmup pass
        engine = CudaBatchEngine(batch_size=b, max_steps=max_steps)
        engine.reset()
        
        start_time = time.time()
        res = engine.run_full_episodes()
        elapsed = res["elapsed_seconds"]
        mem_info = process.memory_info().rss / (1024 * 1024)
        
        entry = {
            "batch_size": b,
            "total_env_steps": res["total_env_steps"],
            "elapsed_seconds": elapsed,
            "steps_per_second": res["steps_per_second"],
            "games_per_second": res["games_per_second"],
            "memory_mb": round(mem_info, 2)
        }
        results.append(entry)
        
        print(f"{b:<8d} | {res['total_env_steps']:<14d} | {elapsed:<12.3f} | {res['steps_per_second']:<14.1f} | {res['games_per_second']:<12.2f} | {mem_info:<10.1f}")

    # Determine sweet spot by maximum games/sec
    optimal = max(results, key=lambda x: x["games_per_second"])
    
    print("\n--------------------------------------------------------------------------")
    print(f"Optimal Operating Sweet Spot: Batch Size {optimal['batch_size']}")
    print(f"Throughput: {optimal['games_per_second']:.1f} games/sec ({optimal['steps_per_second']:,.0f} steps/sec)")
    print("--------------------------------------------------------------------------\n")
    
    report = {
        "id": "STAGE2-BENCHMARK-1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tested_batches": batch_sizes,
        "optimal_batch_size": optimal["batch_size"],
        "max_games_per_sec": optimal["games_per_second"],
        "max_steps_per_sec": optimal["steps_per_second"],
        "profile_results": results
    }
    
    out_path = os.path.join(_PROJECT_ROOT, "reports", "stage2_benchmark_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {out_path}")
    
    return report


if __name__ == "__main__":
    run_stage2_benchmark()
