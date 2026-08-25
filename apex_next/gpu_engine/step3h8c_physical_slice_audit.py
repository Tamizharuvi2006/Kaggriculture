"""Step 3H-8C CUDA movement/carry physical-slice audit."""

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
from apex_next.gpu_engine.step3h_parity_audit import _compare_value  # noqa: E402
from apex_next.gpu_engine.step3h8b_physical_tensor_audit import _object_physical_signature  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8C_PHYSICAL_SLICE_AUDIT.json"


def run_physical_slice_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None
    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    setup_p0 = {"market": [["BUY_ANIMAL", "COW", 1], ["BUY_PRODUCT", "WHEAT", 1]]}
    setup_p1 = {"market": [["BUY_ANIMAL", "GOOSE", 1], ["BUY_PRODUCT", "WHEAT", 1]]}
    cpu.step_market_only([setup_p0 for _ in seeds], [setup_p1 for _ in seeds])
    gpu.step_market_only([setup_p0 for _ in seeds], [setup_p1 for _ in seeds])

    actions = [
        (
            "build_housing",
            {"farmer": ["BUILD_PASTURE"]},
            {"farmer": ["BUILD_COOP"]},
        ),
        (
            "pickup_animal",
            {"farmer": ["PICKUP", "COW", 1]},
            {"farmer": ["PICKUP", "GOOSE", 1]},
        ),
        (
            "place_animal",
            {"farmer": ["PLACE", "COW"]},
            {"farmer": ["PLACE", "GOOSE"]},
        ),
        (
            "pickup_wheat",
            {"farmer": ["PICKUP", "WHEAT", 1]},
            {"farmer": ["PICKUP", "WHEAT", 1]},
        ),
        (
            "move_east",
            {"farmer": ["EAST"]},
            {"farmer": ["EAST"]},
        ),
        (
            "move_west",
            {"farmer": ["WEST"]},
            {"farmer": ["WEST"]},
        ),
        (
            "drop_wheat",
            {"farmer": ["DROP"]},
            {"farmer": ["DROP"]},
        ),
    ]

    reports = []
    for label, action_p0, action_p1 in actions:
        for env_idx in range(len(seeds)):
            cpu._apply_unit_action(env_idx, 0, 0, action_p0.get("farmer", ["PASS"]))
            cpu._apply_unit_action(env_idx, 1, 0, action_p1.get("farmer", ["PASS"]))
        gpu.step_physical_slice([action_p0 for _ in seeds], [action_p1 for _ in seeds])
        if gpu.actual_cuda_used:
            torch.cuda.synchronize(device)
        reports.append({"action": label, "seed_reports": _compare_all(cpu, gpu, seeds)})

    failed = [
        item
        for action_report in reports
        for item in action_report["seed_reports"]
        if item["status"] != "PASS"
    ]
    report = {
        "status": "PASS" if not failed and gpu.actual_cuda_used else "FAIL",
        "step": "STEP 3H-8C - CUDA movement/carry physical slice",
        "scope": "movement, PICKUP, DROP, PLACE, BUILD_PASTURE, BUILD_COOP only; crop/animal lifecycle still pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.tile_kind.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seeds_tested": len(seeds),
        "actions_tested": [label for label, _p0, _p1 in actions],
        "reports": reports,
        "timing_seconds": {"total_wall": round(time.perf_counter() - started, 6)},
        "recommendation": _recommendation(not failed and gpu.actual_cuda_used),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _compare_all(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
) -> list[dict[str, Any]]:
    reports = []
    for env_idx, seed in enumerate(seeds):
        player_reports = []
        for player_idx in range(2):
            expected = _object_physical_signature(cpu, env_idx, player_idx)
            actual = gpu.physical_tensor_signature(env_idx, player_idx)
            divergence = _compare_value(expected, actual, path="")
            object_divergence = _compare_value(_object_snapshot(cpu, env_idx, player_idx), _object_snapshot(gpu, env_idx, player_idx), path="")
            player_reports.append(
                {
                    "player": player_idx,
                    "status": "PASS" if divergence is None and object_divergence is None else "FAIL",
                    "tensor_divergence": divergence,
                    "object_divergence": object_divergence,
                }
            )
        reports.append(
            {
                "seed": seed,
                "status": "PASS" if all(item["status"] == "PASS" for item in player_reports) else "FAIL",
                "players": player_reports,
            }
        )
    return reports


def _object_snapshot(engine: Any, env_idx: int, player_idx: int) -> dict[str, Any]:
    return {
        "farmer": engine.farmers[env_idx, player_idx].detach().cpu().to(torch.int32).tolist()
        if isinstance(engine.farmers, torch.Tensor)
        else engine.farmers[env_idx, player_idx].astype(int).tolist(),
        "hands": [list(pos) for pos in engine.hands[env_idx][player_idx]],
        "tiles": engine.tiles[env_idx][player_idx],
        "shed": engine.private_shed[env_idx][player_idx],
        "inventories": engine.private_inventories[env_idx][player_idx],
    }


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix first CUDA movement/carry divergence before expanding the physical action interpreter."
    return "3H-8C is closed for movement/carry/build/place. Next port PLANT/WATER/HARVEST/FERTILIZE/DIG and lifecycle counters."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8C CUDA physical slice audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_physical_slice_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
