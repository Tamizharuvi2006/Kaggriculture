"""Step 3H-8H CUDA full-step ownership audit."""

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
from apex_next.gpu_engine.step3h_parity_audit import _compare_value  # noqa: E402
from apex_next.gpu_engine.step3h8c_physical_slice_audit import _compare_all  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8H_FULL_STEP_AUDIT.json"


def run_full_step_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    reports = []
    mixed_cpu, mixed_gpu = _new_engines(seeds, device)
    _setup_mixed_step_case(mixed_cpu, mixed_gpu)
    mixed_actions = (
        {"farmer": ["WATER"], "market": [["SELL", "MILK", 1], ["BUY_SEED", "WHEAT", 1]]},
        {"farmer": ["FEED"], "market": [["BUY_PRODUCT", "WHEAT", 1], ["HIRE"]]},
    )
    _run_step_case(mixed_cpu, mixed_gpu, seeds, device, "production_actions_market_crop_decay", mixed_actions, reports)

    boundary_cpu, boundary_gpu = _new_engines(seeds, device)
    _setup_day_boundary_case(boundary_cpu, boundary_gpu)
    boundary_actions = (
        {"farmer": ["CARE"], "hands": [["PICKUP", "WHEAT", 1]], "market": [["BUY_ANIMAL", "COW", 1]]},
        {"farmer": ["WATER"], "market": [["BUY_SEED", "CARROT", 1]]},
    )
    _run_step_case(boundary_cpu, boundary_gpu, seeds, device, "day_boundary_lifecycle_reset", boundary_actions, reports)

    failed = [
        seed_report
        for case_report in reports
        for seed_report in case_report["seed_reports"]
        if seed_report["status"] != "PASS"
    ]
    actual_cuda_used = all(bool(case["actual_cuda_used"]) for case in reports)
    report = {
        "status": "PASS" if not failed and actual_cuda_used else "FAIL",
        "step": "STEP 3H-8H - CUDA full-step ownership",
        "scope": "integrated non-terminal step path only; terminal/reward, full trajectory parity, and benchmarking pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(reports[0]["tensor_device"]) if reports else str(device),
        "actual_cuda_used": actual_cuda_used,
        "seeds_tested": len(seeds),
        "cases_tested": [case["case"] for case in reports],
        "unsupported_actions": sum(case["unsupported_actions"] for case in reports),
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


def _setup_mixed_step_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=4, hour=6, step=102)
    _set_time(gpu, day=4, hour=6, step=102)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            plant = _plant("WHEAT", planted_day=2, watered=False, consecutive_unwatered=0, yield_units=2, max_lifespan_step=102)
            animal = _animal("COW", placed_day=0, fed=False, cared=False, pending_bonus=0, yield_units=0)
            cpu.tiles[env_idx][player_idx][4][4] = dict(plant)
            cpu.tiles[env_idx][player_idx][4][3] = dict(animal)
            gpu.tiles[env_idx][player_idx][4][4] = dict(plant)
            gpu.tiles[env_idx][player_idx][4][3] = dict(animal)
            cpu.plant_tiles[env_idx, player_idx] = 1
            gpu.plant_tiles[env_idx, player_idx] = 1
            cpu.animal_tiles[env_idx, player_idx] = 1
            gpu.animal_tiles[env_idx, player_idx] = 1
            cpu.active_cows[env_idx, player_idx] = 1
            gpu.active_cows[env_idx, player_idx] = 1
            cpu.private_shed[env_idx][player_idx]["WHEAT"] = 2
            gpu.private_shed[env_idx][player_idx]["WHEAT"] = 2
            cpu.private_shed[env_idx][player_idx]["MILK"] = 1
            gpu.private_shed[env_idx][player_idx]["MILK"] = 1
            gpu._sync_physical_tensors(env_idx, player_idx)


def _setup_day_boundary_case(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine) -> None:
    _set_time(cpu, day=7, hour=23, step=191)
    _set_time(gpu, day=7, hour=23, step=191)
    for env_idx in range(cpu.N):
        for player_idx in range(2):
            plant = _plant("TOMATO", planted_day=0, watered=True, consecutive_unwatered=1, yield_units=0, max_lifespan_step=-1)
            animal = _animal("GOOSE", placed_day=3, fed=True, cared=True, pending_bonus=0, yield_units=0)
            cpu.tiles[env_idx][player_idx][4][4] = dict(plant)
            cpu.tiles[env_idx][player_idx][4][3] = dict(animal)
            gpu.tiles[env_idx][player_idx][4][4] = dict(plant)
            gpu.tiles[env_idx][player_idx][4][3] = dict(animal)
            cpu.plant_tiles[env_idx, player_idx] = 1
            gpu.plant_tiles[env_idx, player_idx] = 1
            cpu.animal_tiles[env_idx, player_idx] = 1
            gpu.animal_tiles[env_idx, player_idx] = 1
            cpu.hands[env_idx][player_idx] = [[4, 4]]
            gpu.hands[env_idx][player_idx] = [[4, 4]]
            cpu.private_inventories[env_idx][player_idx] = [{}, {"WHEAT": 1}]
            gpu.private_inventories[env_idx][player_idx] = [{}, {"WHEAT": 1}]
            cpu.workers[env_idx, player_idx] = 1
            gpu.workers[env_idx, player_idx] = 1
            cpu.private_shed[env_idx][player_idx]["WHEAT"] = 2
            gpu.private_shed[env_idx][player_idx]["WHEAT"] = 2
            gpu._sync_physical_tensors(env_idx, player_idx)


def _run_step_case(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
    device: torch.device,
    label: str,
    actions: tuple[dict[str, Any], dict[str, Any]],
    reports: list[dict[str, Any]],
) -> None:
    p0, p1 = actions
    action_batches_p0 = [p0 for _ in seeds]
    action_batches_p1 = [p1 for _ in seeds]
    unsupported = _unsupported_count([p0, p1])
    cpu.step(action_batches_p0, action_batches_p1)
    gpu.step_integrated(action_batches_p0, action_batches_p1)
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    physical_reports = _compare_all(cpu, gpu, seeds)
    full_reports = []
    for env_idx, seed in enumerate(seeds):
        divergence = _compare_value(_state_snapshot(cpu, env_idx), _state_snapshot(gpu, env_idx), path="")
        physical_status = physical_reports[env_idx]["status"]
        full_reports.append(
            {
                "seed": seed,
                "status": "PASS" if divergence is None and physical_status == "PASS" else "FAIL",
                "full_state_divergence": divergence,
                "physical": physical_reports[env_idx],
            }
        )
    reports.append(
        {
            "case": label,
            "status": "PASS" if all(item["status"] == "PASS" for item in full_reports) else "FAIL",
            "unsupported_actions": unsupported,
            "tensor_device": str(gpu.tile_kind.device),
            "actual_cuda_used": bool(gpu.actual_cuda_used),
            "seed_reports": full_reports,
        }
    )


def _state_snapshot(engine: Any, env_idx: int) -> dict[str, Any]:
    return {
        "step": int(engine.step_idx),
        "day": int(engine.day_idx),
        "hour": int(engine.hour_idx),
        "money": _array2(engine.money, env_idx),
        "land_count": _array2(engine.land_count, env_idx),
        "workers": _array2(engine.workers, env_idx),
        "hires_today": _array2(engine.hires_today, env_idx),
        "active_cows": _array2(engine.active_cows, env_idx),
        "active_sheep": _array2(engine.active_sheep, env_idx),
        "plant_tiles": _array2(engine.plant_tiles, env_idx),
        "animal_tiles": _array2(engine.animal_tiles, env_idx),
        "public_inventory": _array3(engine.public_inventory, env_idx),
        "market_inventory": _array1(engine.market_inventory, env_idx),
        "market_prices": _array1(engine.market_prices, env_idx),
        "town_shops": list(engine.town_shops[env_idx]),
        "unlocked_quadrants": [list(engine.unlocked_quadrants[env_idx][0]), list(engine.unlocked_quadrants[env_idx][1])],
    }


def _array1(value: Any, env_idx: int) -> list[Any]:
    item = value[env_idx]
    if isinstance(item, torch.Tensor):
        return item.detach().cpu().tolist()
    return np.asarray(item).tolist()


def _array2(value: Any, env_idx: int) -> list[Any]:
    item = value[env_idx]
    if isinstance(item, torch.Tensor):
        return item.detach().cpu().tolist()
    return np.asarray(item).tolist()


def _array3(value: Any, env_idx: int) -> list[Any]:
    item = value[env_idx]
    if isinstance(item, torch.Tensor):
        return item.detach().cpu().tolist()
    return np.asarray(item).tolist()


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


def _set_time(engine: Any, day: int, hour: int, step: int) -> None:
    engine.day_idx = day
    engine.hour_idx = hour
    engine.step_idx = step


def _unsupported_count(actions: list[dict[str, Any]]) -> int:
    supported = {
        "PASS",
        "NORTH",
        "SOUTH",
        "EAST",
        "WEST",
        "DROP",
        "PICKUP",
        "PLACE",
        "BUILD_PASTURE",
        "BUILD_COOP",
        "PLANT",
        "WATER",
        "HARVEST",
        "FERTILIZE",
        "DIG",
        "FEED",
        "CARE",
        "COLLECT_FERTILIZER",
    }
    count = 0
    for action in actions:
        for key in ("farmer",):
            op = action.get(key, ["PASS"])
            if isinstance(op, list) and op and op[0] not in supported:
                count += 1
        for hand_action in action.get("hands", []) if isinstance(action.get("hands", []), list) else []:
            if isinstance(hand_action, list) and hand_action and hand_action[0] not in supported:
                count += 1
    return count


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix first CUDA full-step divergence before terminal/reward or trajectory parity."
    return "3H-8H is closed for full-step ownership. Next implement terminal/reward semantics as a separate gate."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8H CUDA full-step ownership audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_full_step_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
