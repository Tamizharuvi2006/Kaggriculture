"""Step 3H-6 performance benchmark for parity-correct PairedSimV2.

This benchmark intentionally measures the corrected NumPy/Python simulator
only. It does not run PPO, does not convert to CUDA, and does not use the fast
engine as a new source of truth.
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_sim_v2 import PairedSimV2Engine  # noqa: E402
from apex_next.gpu_engine.step3h_parity_audit import _run_real_kaggle  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "parity" / "STEP3H_PERFORMANCE_BENCHMARK.json"
DEFAULT_BATCH_SIZES = [256, 512, 1024, 2048, 4096, 8192]


def run_performance_benchmark(
    batch_sizes: list[int],
    trace_seed: int = 39000,
    seed_start: int = 50000,
    steps: int = 720,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    started = time.perf_counter()
    trace_started = time.perf_counter()
    actions, real_snapshots = _run_real_kaggle(seed=trace_seed, steps=steps)
    trace_seconds = time.perf_counter() - trace_started
    steps_per_game = len(actions)

    results = []
    for batch_size in batch_sizes:
        print(f"benchmark batch_size={batch_size}", flush=True)
        resource_before_start = time.perf_counter()
        before = _resource_snapshot()
        resource_snapshot_seconds = time.perf_counter() - resource_before_start
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        errors = 0
        terminal_count = 0
        sim = PairedSimV2Engine(seed=seed_start)
        reset_seconds = 0.0
        step_loop_seconds = 0.0

        for offset in range(batch_size):
            reset_start = time.perf_counter()
            sim.reset(seed_start + offset)
            reset_seconds += time.perf_counter() - reset_start
            done = False
            try:
                step_start = time.perf_counter()
                for action_pair in actions:
                    _, _, done, _ = sim.step(action_pair["p0"], action_pair["p1"])
                step_loop_seconds += time.perf_counter() - step_start
                if done:
                    terminal_count += 1
            except Exception:
                errors += 1

        wall_seconds = time.perf_counter() - wall_start
        cpu_seconds = time.process_time() - cpu_start
        resource_after_start = time.perf_counter()
        after = _resource_snapshot()
        resource_snapshot_seconds += time.perf_counter() - resource_after_start
        total_steps = batch_size * steps_per_game
        result = {
            "batch_size": batch_size,
            "total_games": batch_size,
            "steps_per_game": steps_per_game,
            "total_steps": total_steps,
            "wall_seconds": round(wall_seconds, 6),
            "process_cpu_seconds": round(cpu_seconds, 6),
            "approx_process_cpu_util_percent": round(
                (cpu_seconds / max(wall_seconds, 1e-9)) * 100.0 / max(os.cpu_count() or 1, 1),
                2,
            ),
            "games_per_second": round(batch_size / max(wall_seconds, 1e-9), 3),
            "steps_per_second": round(total_steps / max(wall_seconds, 1e-9), 0),
            "terminal_count": terminal_count,
            "errors": errors,
            "timing_breakdown": {
                "sim_reset_seconds": round(reset_seconds, 6),
                "sim_step_replay_loop_seconds": round(step_loop_seconds, 6),
                "resource_snapshot_seconds": round(resource_snapshot_seconds, 6),
                "serialization_report_write_seconds": None,
                "python_loop_and_other_seconds": round(
                    max(0.0, wall_seconds - reset_seconds - step_loop_seconds),
                    6,
                ),
            },
            "resources_before": before,
            "resources_after": after,
        }
        print(
            f"batch_size={batch_size} games_sec={result['games_per_second']} "
            f"steps_sec={result['steps_per_second']} wall={result['wall_seconds']}s "
            f"errors={errors}",
            flush=True,
        )
        results.append(result)
        write_start = time.perf_counter()
        _write_report(
            report_path,
            batch_sizes=batch_sizes,
            results=results,
            trace_seed=trace_seed,
            steps=steps,
            real_steps=len(real_snapshots) - 1,
            action_steps=steps_per_game,
            trace_seconds=trace_seconds,
            started=started,
            partial=True,
        )
        result["timing_breakdown"]["serialization_report_write_seconds"] = round(
            time.perf_counter() - write_start,
            6,
        )
        _write_report(
            report_path,
            batch_sizes=batch_sizes,
            results=results,
            trace_seed=trace_seed,
            steps=steps,
            real_steps=len(real_snapshots) - 1,
            action_steps=steps_per_game,
            trace_seconds=trace_seconds,
            started=started,
            partial=True,
        )

    best = max(results, key=lambda item: item["games_per_second"]) if results else None
    report = _build_report(
        batch_sizes=batch_sizes,
        results=results,
        trace_seed=trace_seed,
        steps=steps,
        real_steps=len(real_snapshots) - 1,
        action_steps=steps_per_game,
        trace_seconds=trace_seconds,
        started=started,
        partial=False,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _write_report(
    report_path: Path,
    *,
    batch_sizes: list[int],
    results: list[dict[str, Any]],
    trace_seed: int,
    steps: int,
    real_steps: int,
    action_steps: int,
    trace_seconds: float,
    started: float,
    partial: bool,
) -> None:
    report = _build_report(
        batch_sizes=batch_sizes,
        results=results,
        trace_seed=trace_seed,
        steps=steps,
        real_steps=real_steps,
        action_steps=action_steps,
        trace_seconds=trace_seconds,
        started=started,
        partial=partial,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _build_report(
    *,
    batch_sizes: list[int],
    results: list[dict[str, Any]],
    trace_seed: int,
    steps: int,
    real_steps: int,
    action_steps: int,
    trace_seconds: float,
    started: float,
    partial: bool,
) -> dict[str, Any]:
    best = max(results, key=lambda item: item["games_per_second"]) if results else None
    report = {
        "status": "PARTIAL" if partial else ("PASS" if results and all(item["errors"] == 0 for item in results) else "FAIL"),
        "step": "STEP 3H-6 - PairedSimV2 performance benchmark",
        "scope": "performance baseline only; no simulator mechanics changes, no CUDA conversion, no PPO",
        "backend": "NumPy/Python PairedSimV2",
        "actual_cuda_used": False,
        "invokes_vectorized_batch_engine": False,
        "benchmark_method": (
            "Cached real action trace replayed through PairedSimV2 one game at a time; "
            "this profiles the parity-correct Python/NumPy simulator path, not V25 vectorized batch simulation."
        ),
        "trace_source": {
            "seed": trace_seed,
            "steps_requested": steps,
            "real_steps_recorded": real_steps,
            "cached_action_steps": action_steps,
            "trace_generation_seconds": round(trace_seconds, 6),
        },
        "batch_sizes": batch_sizes,
        "completed_batch_sizes": [item["batch_size"] for item in results],
        "results": results,
        "best_by_games_per_second": best,
        "recommendation": _recommendation(best),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    return report


def _recommendation(best: dict[str, Any] | None) -> str:
    if not best:
        return "Benchmark failed before producing usable throughput results."
    return (
        f"Corrected NumPy/Python PairedSimV2 peak measured at batch size {best['batch_size']} "
        f"with {best['games_per_second']} games/sec and {best['steps_per_second']:.0f} steps/sec. "
        "Use this as the clean CPU baseline before deciding whether CUDA conversion is worth it."
    )


def _resource_snapshot() -> dict[str, Any]:
    return {
        "nvidia_smi": _nvidia_smi(),
        "process_rss_mb": _current_process_rss_mb(),
        "logical_cpu_count": os.cpu_count(),
    }


def _nvidia_smi() -> dict[str, Any] | None:
    query = "utilization.gpu,memory.used,memory.total"
    try:
        proc = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = [part.strip() for part in proc.stdout.strip().split(",")]
    if len(parts) < 3:
        return {"raw": proc.stdout.strip()}
    return {
        "gpu_util_percent": _safe_float(parts[0]),
        "gpu_memory_used_mb": _safe_float(parts[1]),
        "gpu_memory_total_mb": _safe_float(parts[2]),
    }


def _current_process_rss_mb() -> float | None:
    try:
        import psutil  # type: ignore

        return float(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
    except Exception:
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_batch_sizes(value: str) -> list[int]:
    if not value:
        return DEFAULT_BATCH_SIZES
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-6 PairedSimV2 performance benchmark.")
    parser.add_argument("--batch-sizes", type=str, default=",".join(str(v) for v in DEFAULT_BATCH_SIZES))
    parser.add_argument("--trace-seed", type=int, default=39000)
    parser.add_argument("--seed-start", type=int, default=50000)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_performance_benchmark(
        _parse_batch_sizes(args.batch_sizes),
        trace_seed=args.trace_seed,
        seed_start=args.seed_start,
        steps=args.steps,
        report_path=args.report,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
