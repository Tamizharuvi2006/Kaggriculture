"""Profile the cached-trace CPU/CUDA replay hot path for Step 3H-8K."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_cuda_engine import CorrectedCudaPairedEngine  # noqa: E402
from apex_next.gpu_engine.paired_gpu_v25.corrected_vector_engine import CorrectedVectorPairedEngine  # noqa: E402
from apex_next.gpu_engine.step3h8j_full_cuda_trajectory_audit import DEFAULT_TRACE_DIR, _load_or_create_trace  # noqa: E402
from apex_next.gpu_engine.step3h8k_multiseed_cuda_parity import (  # noqa: E402
    _numeric_state_divergence,
    _object_state_divergence,
    _physical_tensor_divergence,
)


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "profiles" / "STEP3H8K_HOTPATH_PROFILE.json"


def run_hotpath_profile(
    seeds: list[int],
    steps: int,
    report_path: Path,
    trace_dir: Path = DEFAULT_TRACE_DIR,
) -> dict[str, Any]:
    started = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    traces = [_load_or_create_trace(seed, 720, trace_dir, collect_missing_trace=True) for seed in seeds]
    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    timings = {
        "cpu_step": 0.0,
        "gpu_step_integrated": 0.0,
        "cuda_synchronize": 0.0,
        "numeric_compare": 0.0,
        "object_compare": 0.0,
        "tensor_compare": 0.0,
    }
    first_divergence = None
    max_steps = min(steps, min(len(trace["actions"]) for trace in traces))
    for step_idx in range(1, max_steps + 1):
        action_batches_p0 = [trace["actions"][step_idx - 1]["p0"] for trace in traces]
        action_batches_p1 = [trace["actions"][step_idx - 1]["p1"] for trace in traces]

        section = time.perf_counter()
        cpu.step(action_batches_p0, action_batches_p1)
        timings["cpu_step"] += time.perf_counter() - section

        section = time.perf_counter()
        gpu.step_integrated(action_batches_p0, action_batches_p1)
        timings["gpu_step_integrated"] += time.perf_counter() - section

        if gpu.actual_cuda_used:
            section = time.perf_counter()
            torch.cuda.synchronize(device)
            timings["cuda_synchronize"] += time.perf_counter() - section

        section = time.perf_counter()
        numeric = _numeric_state_divergence(cpu, gpu)
        timings["numeric_compare"] += time.perf_counter() - section

        section = time.perf_counter()
        objects = _object_state_divergence(cpu, gpu)
        timings["object_compare"] += time.perf_counter() - section

        section = time.perf_counter()
        tensors = _physical_tensor_divergence(gpu)
        timings["tensor_compare"] += time.perf_counter() - section

        if numeric is not None or objects is not None or tensors is not None:
            first_divergence = {
                "step": step_idx,
                "numeric": numeric,
                "object": objects,
                "tensor": tensors,
            }
            break

    total_profiled = sum(timings.values())
    report = {
        "status": "PASS" if first_divergence is None and gpu.actual_cuda_used else "FAIL",
        "step": "STEP 3H-8K hotpath profile",
        "seeds": seeds,
        "steps_profiled": max_steps,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "tensor_device": str(gpu.money.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "first_divergence": first_divergence,
        "timing_seconds": {key: round(value, 6) for key, value in timings.items()},
        "timing_share": {
            key: 0.0 if total_profiled <= 0 else round(value / total_profiled, 6)
            for key, value in timings.items()
        },
        "total_profiled_seconds": round(total_profiled, 6),
        "total_wall_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Step 3H-8K replay hot path.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    print(json.dumps(run_hotpath_profile(_parse_seeds(args), args.steps, args.report), indent=2))


if __name__ == "__main__":
    main()
