"""Step 3H-8G CUDA daily animal lifecycle audit."""

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
from apex_next.gpu_engine.step3h8c_physical_slice_audit import _compare_all  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8G_ANIMAL_LIFECYCLE_AUDIT.json"


def run_animal_lifecycle_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    reports = []
    refresh_cpu, refresh_gpu = _new_engines(seeds, device)
    _setup_refresh_case(refresh_cpu, refresh_gpu)
    refresh_reports = _apply_animal_refresh(refresh_cpu, refresh_gpu, seeds, device)
    reports.append({"case": "daily_refresh_yield_bonus_and_reset", "seed_reports": refresh_reports})

    removal_cpu, removal_gpu = _new_engines(seeds, device)
    _setup_removal_case(removal_cpu, removal_gpu)
    removal_reports = _apply_animal_refresh(removal_cpu, removal_gpu, seeds, device)
    reports.append({"case": "unfed_removal_to_housing", "seed_reports": removal_reports})

    failed = [
        item
        for case_report in reports
        for item in case_report["seed_reports"]
        if item["status"] != "PASS"
    ]
    actual_cuda_used = bool(refresh_gpu.actual_cuda_used and removal_gpu.actual_cuda_used)
    report = {
        "status": "PASS" if not failed and actual_cuda_used else "FAIL",
        "step": "STEP 3H-8G - CUDA daily animal lifecycle",
        "scope": "daily animal refresh/yield/feed-care progression/removal only; full step, terminal, and benchmarking pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(refresh_gpu.tile_kind.device),
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


def _setup_refresh_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=7, hour=23, step=191)
    _set_time(gpu, day=7, hour=23, step=191)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            animals = [
                (4, 4, _animal("GOOSE", placed_day=3, fed=True, cared=True, pending_bonus=0, yield_units=0)),
                (3, 4, _animal("COW", placed_day=0, fed=True, cared=False, pending_bonus=1, yield_units=5)),
                (4, 3, _animal("SHEEP", placed_day=1, fed=False, cared=True, pending_bonus=0, yield_units=0, consecutive_unfed=0)),
            ]
            for x, y, tile in animals:
                cpu.tiles[env_idx][player_idx][y][x] = dict(tile)
                gpu.tiles[env_idx][player_idx][y][x] = dict(tile)
            cpu.animal_tiles[env_idx, player_idx] = len(animals)
            gpu.animal_tiles[env_idx, player_idx] = len(animals)
            gpu._sync_physical_tensors(env_idx, player_idx)


def _setup_removal_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=5, hour=23, step=143)
    _set_time(gpu, day=5, hour=23, step=143)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            animals = [
                (4, 4, _animal("COW", placed_day=0, fed=False, cared=False, pending_bonus=0, yield_units=0, consecutive_unfed=1)),
                (3, 4, _animal("GOOSE", placed_day=0, fed=False, cared=False, pending_bonus=0, yield_units=0, consecutive_unfed=1)),
            ]
            for x, y, tile in animals:
                cpu.tiles[env_idx][player_idx][y][x] = dict(tile)
                gpu.tiles[env_idx][player_idx][y][x] = dict(tile)
            cpu.animal_tiles[env_idx, player_idx] = len(animals)
            gpu.animal_tiles[env_idx, player_idx] = len(animals)
            gpu._sync_physical_tensors(env_idx, player_idx)


def _animal(
    animal: str,
    placed_day: int,
    fed: bool,
    cared: bool,
    pending_bonus: int,
    yield_units: int,
    consecutive_unfed: int = 0,
) -> dict[str, Any]:
    return {
        "kind": "PASTURE" if animal in ("COW", "SHEEP") else "COOP",
        "animal": animal,
        "placed_day": placed_day,
        "yield_units": yield_units,
        "fed_today": fed,
        "cared_today": cared,
        "fertilizer_available": False,
        "consecutive_unfed": consecutive_unfed,
        "pending_care_bonus": pending_bonus,
    }


def _apply_animal_refresh(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
    device: torch.device,
) -> list[dict[str, Any]]:
    for env_idx in range(len(seeds)):
        for player_idx in range(2):
            cpu._daily_refresh_animals(env_idx, player_idx)
    gpu.daily_animal_lifecycle_slice()
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    return _compare_all(cpu, gpu, seeds)


def _set_time(engine: Any, day: int, hour: int, step: int) -> None:
    engine.day_idx = day
    engine.hour_idx = hour
    engine.step_idx = step


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix first CUDA animal lifecycle divergence before full-step ownership."
    return "3H-8G is closed for daily animal lifecycle. Next integrate full-step ownership without terminal benchmarking."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8G CUDA daily animal lifecycle audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_animal_lifecycle_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
