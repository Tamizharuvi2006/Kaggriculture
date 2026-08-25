"""Step 3H-8 CUDA port audit.

This validates the first CUDA backend slice against the parity-correct CPU
vector engine. Scope is intentionally limited to numeric reset and market
transition until physical tile/lifecycle state is encoded numerically.
"""

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
from apex_next.gpu_engine.step3h7_vector_port_audit import _projection, _vector_initial  # noqa: E402
from apex_next.gpu_engine.step3h_parity_audit import _compare_value, _run_real_kaggle  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8_CUDA_PORT_AUDIT.json"


def run_cuda_audit(seeds: list[int], steps: int = 1, report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else None
    device = torch.device("cuda" if cuda_available else "cpu")

    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    initial_reports = []
    for env_idx, seed in enumerate(seeds):
        cpu_projection = _vector_initial(cpu, env_idx)
        gpu_projection = _cuda_projection(gpu, env_idx)
        initial_reports.append(
            {
                "seed": seed,
                "status": "PASS" if _compare_value(cpu_projection, gpu_projection, path="") is None else "FAIL",
                "cpu_vs_cuda_divergence": _compare_value(cpu_projection, gpu_projection, path=""),
            }
        )

    traces = []
    for seed in seeds:
        actions, _ = _run_real_kaggle(seed=seed, steps=steps)
        if len(actions) != steps:
            raise RuntimeError(f"Seed {seed} produced {len(actions)} actions, expected {steps}")
        traces.append(actions)

    market_started = time.perf_counter()
    for step_idx in range(steps):
        actions_p0 = [trace[step_idx]["p0"] for trace in traces]
        actions_p1 = [trace[step_idx]["p1"] for trace in traces]
        cpu.step_market_only(actions_p0, actions_p1)
        gpu.step_market_only(actions_p0, actions_p1)
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    market_elapsed = time.perf_counter() - market_started

    market_reports = []
    for env_idx, seed in enumerate(seeds):
        cpu_projection = _vector_initial(cpu, env_idx)
        gpu_projection = _cuda_projection(gpu, env_idx)
        divergence = _compare_value(cpu_projection, gpu_projection, path="")
        market_reports.append(
            {
                "seed": seed,
                "status": "PASS" if divergence is None else "FAIL",
                "cpu_vs_cuda_divergence": divergence,
                "market_prices": gpu_projection["market"]["prices"],
            }
        )

    initial_passed = sum(1 for item in initial_reports if item["status"] == "PASS")
    market_passed = sum(1 for item in market_reports if item["status"] == "PASS")
    report = {
        "status": "PASS" if initial_passed == len(seeds) and market_passed == len(seeds) and gpu.actual_cuda_used else "FAIL",
        "step": "STEP 3H-8A - CUDA numeric reset/market parity",
        "scope": "numeric CUDA tensors for reset + market/order transition only; physical tiles not CUDA-ported yet",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.money.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seeds_tested": len(seeds),
        "steps_tested": steps,
        "initial_passed": initial_passed,
        "market_passed": market_passed,
        "initial_reports": initial_reports,
        "market_reports": market_reports,
        "timing_seconds": {"cuda_market_slice": round(market_elapsed, 6), "total_wall": round(time.perf_counter() - started, 6)},
        "recommendation": _recommendation(gpu.actual_cuda_used, market_passed, len(seeds)),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _cuda_projection(engine: CorrectedCudaPairedEngine, env_idx: int) -> dict[str, Any]:
    obs = engine.observation(env_idx, 0)
    return _projection(
        step=obs.get("step", 0),
        day=obs.get("day", 0),
        hour=obs.get("hour", 0),
        farms=obs.get("farms", []),
        market=obs.get("market", {}),
        town=obs.get("town", {}),
        privates=[engine.private_observation(env_idx, 0), engine.private_observation(env_idx, 1)],
    )


def _recommendation(cuda_used: bool, passed: int, total: int) -> str:
    if not cuda_used:
        return "CUDA tensors were not active. Fix local CUDA availability before expanding Step 3H-8."
    if passed == total:
        return "3H-8A CUDA numeric reset/market parity is closed. Next encode physical tile/action state numerically before full CUDA parity."
    return "CUDA market parity failed. Fix the first divergence before porting physical mechanics."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8 CUDA numeric parity audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_cuda_audit(_parse_seeds(args), steps=args.steps, report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
