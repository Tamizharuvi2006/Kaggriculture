"""Benchmark the parity-correct CUDA engine without real-environment calls.

The benchmark reuses one cached real action trace as a deterministic workload.
It measures only ``CorrectedCudaPairedEngine.step_integrated`` and never runs
Kaggriculture or PPO updates.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_cuda_engine import CorrectedCudaPairedEngine  # noqa: E402


DEFAULT_TRACE = PROJECT_ROOT / "reports" / "step3h" / "traces" / "step3h_real_action_traces" / "real_action_trace_seed_39000_steps_720.json"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8M_CORRECTED_CUDA_PERFORMANCE.json"


def _nvidia_metrics() -> dict[str, float | None]:
    query = "utilization.gpu,memory.used,memory.total"
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        values = [float(part.strip()) for part in result.stdout.strip().split(",")]
        return {
            "gpu_utilization_percent": values[0],
            "vram_used_mb": values[1],
            "vram_total_mb": values[2],
        }
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return {"gpu_utilization_percent": None, "vram_used_mb": None, "vram_total_mb": None}


def _load_actions(trace_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    actions = payload["actions"]
    if len(actions) != 719:
        raise ValueError(f"Expected 719 cached actions, got {len(actions)}")
    return actions


def _run_batch(batch_size: int, actions: list[dict[str, Any]], device: torch.device) -> dict[str, Any]:
    engine = CorrectedCudaPairedEngine(batch_size=batch_size, base_seed=39000, device=device)
    action_p0 = [item["p0"] for item in actions]
    action_p1 = [item["p1"] for item in actions]
    batch_p0 = [action_p0[0] for _ in range(batch_size)]
    batch_p1 = [action_p1[0] for _ in range(batch_size)]

    # Short warmup establishes CUDA kernels and allocator state without entering the timed run.
    engine.step_integrated(batch_p0, batch_p1)
    if engine.actual_cuda_used:
        torch.cuda.synchronize(device)
    engine.reset(list(range(39000, 39000 + batch_size)))
    if engine.actual_cuda_used:
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.synchronize(device)

    process = psutil.Process(os.getpid())
    cpu_before = psutil.cpu_percent(interval=0.1)
    ram_before = process.memory_info().rss / (1024 * 1024)
    gpu_before = _nvidia_metrics()
    started = time.perf_counter()
    for action in actions:
        batch_p0 = [action["p0"] for _ in range(batch_size)]
        batch_p1 = [action["p1"] for _ in range(batch_size)]
        engine.step_integrated(batch_p0, batch_p1)
    if engine.actual_cuda_used:
        torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started
    cpu_after = psutil.cpu_percent(interval=0.1)
    ram_after = process.memory_info().rss / (1024 * 1024)
    gpu_after = _nvidia_metrics()
    peak_vram = (
        torch.cuda.max_memory_allocated(device) / (1024 * 1024)
        if engine.actual_cuda_used
        else None
    )
    return {
        "batch_size": batch_size,
        "games": batch_size,
        "steps_per_game": len(actions),
        "total_steps": batch_size * len(actions),
        "wall_time_seconds": round(elapsed, 6),
        "games_per_second": round(batch_size / elapsed, 4),
        "steps_per_second": round(batch_size * len(actions) / elapsed, 2),
        "simulation_time_seconds": round(elapsed, 6),
        "ppo_update_time_seconds": 0.0,
        "ppo_update_status": "NOT_RUN",
        "gpu_before": gpu_before,
        "gpu_after": gpu_after,
        "cuda_peak_allocated_mb": round(peak_vram, 3) if peak_vram is not None else None,
        "cpu_percent_before": cpu_before,
        "cpu_percent_after": cpu_after,
        "process_ram_before_mb": round(ram_before, 3),
        "process_ram_after_mb": round(ram_after, 3),
        "actual_cuda_used": bool(engine.actual_cuda_used),
        "tensor_device": str(engine.money.device),
    }


def run_benchmark(trace_path: Path, report_path: Path, batch_sizes: list[int]) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing to benchmark a CPU fallback")
    device = torch.device("cuda:0")
    actions = _load_actions(trace_path)
    results = [_run_batch(batch, actions, device) for batch in batch_sizes]
    report = {
        "status": "PASS" if all(item["actual_cuda_used"] for item in results) else "FAIL",
        "step": "STEP 3H-8M - Corrected CUDA performance benchmark",
        "scope": "CUDA engine only; cached action workload; no real Kaggriculture generation; no PPO update",
        "trace_path": str(trace_path),
        "trace_actions": len(actions),
        "cuda_available": True,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "tensor_device": "cuda:0",
        "batch_sizes": batch_sizes,
        "results": results,
        "acceptance": {
            "real_environment_not_called": True,
            "ppo_not_run": True,
            "all_actual_cuda_used": all(item["actual_cuda_used"] for item in results),
            "all_tensor_device_cuda0": all(item["tensor_device"] == "cuda:0" for item in results),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[256, 512, 1024, 2048, 4096])
    args = parser.parse_args()
    report = run_benchmark(args.trace, args.report, args.batch_sizes)
    for result in report["results"]:
        print(
            f"batch={result['batch_size']} wall={result['wall_time_seconds']:.3f}s "
            f"games_per_sec={result['games_per_second']:.3f} "
            f"steps_per_sec={result['steps_per_second']:.1f} "
            f"cuda={result['actual_cuda_used']}"
        )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
