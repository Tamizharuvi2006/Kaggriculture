"""Step 3H-8F CUDA daily crop lifecycle audit."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_cuda_engine import CorrectedCudaPairedEngine  # noqa: E402
from apex_next.gpu_engine.paired_gpu_v25.corrected_vector_engine import CorrectedVectorPairedEngine  # noqa: E402
from apex_next.gpu_engine.step3h8c_physical_slice_audit import _compare_all  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8F_CROP_LIFECYCLE_AUDIT.json"


def run_crop_lifecycle_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    reports = []
    daily_cpu, daily_gpu = _new_engines(seeds, device)
    _setup_daily_refresh_case(daily_cpu, daily_gpu)
    daily_cpu_reports = _apply_daily_refresh(daily_cpu, daily_gpu, seeds, device)
    reports.append({"case": "daily_refresh_growth_and_weed", "seed_reports": daily_cpu_reports})

    decay_cpu, decay_gpu = _new_engines(seeds, device)
    _setup_decay_case(decay_cpu, decay_gpu)
    decay_reports = _apply_decay(decay_cpu, decay_gpu, seeds, device)
    reports.append({"case": "lifespan_decay_to_weed", "seed_reports": decay_reports})

    failed = [
        item
        for case_report in reports
        for item in case_report["seed_reports"]
        if item["status"] != "PASS"
    ]
    actual_cuda_used = bool(daily_gpu.actual_cuda_used and decay_gpu.actual_cuda_used)
    report = {
        "status": "PASS" if not failed and actual_cuda_used else "FAIL",
        "step": "STEP 3H-8F - CUDA daily crop lifecycle",
        "scope": "daily crop refresh/growth and crop lifespan decay only; animal lifecycle, full step, terminal, and benchmarking pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(daily_gpu.tile_kind.device),
        "actual_cuda_used": actual_cuda_used,
        "seeds_tested": len(seeds),
        "cases_tested": [case["case"] for case in reports],
        "reports": reports,
        "timing_seconds": {"total_wall": round(time.perf_counter() - started, 6)},
        "recommendation": _recommendation(not failed and actual_cuda_used),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _new_engines(
    seeds: list[int],
    device: torch.device,
) -> tuple[CorrectedVectorPairedEngine, CorrectedCudaPairedEngine]:
    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)
    return cpu, gpu


def _setup_daily_refresh_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=7, hour=23, step=191)
    _set_time(gpu, day=7, hour=23, step=191)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            crop_tiles = [
                (4, 4, _plant("WHEAT", planted_day=5, watered=True, consecutive_unwatered=1, yield_units=1, max_lifespan_step=240)),
                (3, 4, _plant("WHEAT", planted_day=5, watered=False, consecutive_unwatered=1, yield_units=1, max_lifespan_step=240)),
                (4, 3, _plant("TOMATO", planted_day=0, watered=True, consecutive_unwatered=1, yield_units=0, max_lifespan_step=-1, fertilized_until_day=7)),
            ]
            for x, y, tile in crop_tiles:
                cpu.tiles[env_idx][player_idx][y][x] = dict(tile)
                gpu.tiles[env_idx][player_idx][y][x] = dict(tile)
            cpu.plant_tiles[env_idx, player_idx] = len(crop_tiles)
            gpu.plant_tiles[env_idx, player_idx] = len(crop_tiles)
            gpu._sync_physical_tensors(env_idx, player_idx)


def _setup_decay_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=10, hour=4, step=244)
    _set_time(gpu, day=10, hour=4, step=244)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            tile = _plant("WHEAT", planted_day=5, watered=False, consecutive_unwatered=0, yield_units=1, max_lifespan_step=244)
            cpu.tiles[env_idx][player_idx][4][4] = dict(tile)
            gpu.tiles[env_idx][player_idx][4][4] = dict(tile)
            cpu.plant_tiles[env_idx, player_idx] = 1
            gpu.plant_tiles[env_idx, player_idx] = 1
            gpu._sync_physical_tensors(env_idx, player_idx)


def _plant(
    crop: str,
    planted_day: int,
    watered: bool,
    consecutive_unwatered: int,
    yield_units: int,
    max_lifespan_step: int,
    fertilized_until_day: int = -1,
) -> dict[str, Any]:
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "watered_today": watered,
        "consecutive_unwatered": consecutive_unwatered,
        "yield_units": yield_units,
        "max_lifespan_step": max_lifespan_step,
        "fertilized_until_day": fertilized_until_day,
    }


def _apply_daily_refresh(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
    device: torch.device,
) -> list[dict[str, Any]]:
    for env_idx in range(len(seeds)):
        for player_idx in range(2):
            cpu._daily_refresh_plants(env_idx, player_idx)
    gpu.daily_crop_lifecycle_slice()
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    return _compare_all(cpu, gpu, seeds)


def _apply_decay(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
    device: torch.device,
) -> list[dict[str, Any]]:
    for env_idx in range(len(seeds)):
        for player_idx in range(2):
            cpu._decay_plants(env_idx, player_idx)
    gpu.crop_decay_slice()
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    return _compare_all(cpu, gpu, seeds)


def _set_time(engine: Any, day: int, hour: int, step: int) -> None:
    engine.day_idx = day
    engine.hour_idx = hour
    engine.step_idx = step


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix first CUDA crop lifecycle divergence before animal lifecycle or full-step work."
    return "3H-8F is closed for daily crop lifecycle. Next port daily animal lifecycle as a separate gate."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8F CUDA daily crop lifecycle audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_crop_lifecycle_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
