"""Step 3H-8E CUDA animal-action physical-slice audit."""

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


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8E_ANIMAL_ACTION_AUDIT.json"


def run_animal_action_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    _setup_animals(cpu, gpu, seeds)

    reports = []
    action_sequence = [
        ("feed", {"farmer": ["FEED"]}),
        ("care", {"farmer": ["CARE"]}),
        ("collect_fertilizer", {"farmer": ["COLLECT_FERTILIZER"]}),
    ]

    for label, action in action_sequence:
        for env_idx in range(len(seeds)):
            cpu._apply_unit_action(env_idx, 0, 0, action.get("farmer", ["PASS"]))
            cpu._apply_unit_action(env_idx, 1, 0, action.get("farmer", ["PASS"]))
        gpu.step_physical_slice([action for _ in seeds], [action for _ in seeds])
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
        "step": "STEP 3H-8E - CUDA animal action physical slice",
        "scope": "FEED, CARE, COLLECT_FERTILIZER only; daily animal lifecycle and full step ownership pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.tile_kind.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seeds_tested": len(seeds),
        "actions_tested": [label for label, _action in action_sequence],
        "reports": reports,
        "timing_seconds": {"total_wall": round(time.perf_counter() - started, 6)},
        "recommendation": _recommendation(not failed and gpu.actual_cuda_used),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _setup_animals(cpu: CorrectedVectorPairedEngine, gpu: CorrectedCudaPairedEngine, seeds: list[int]) -> None:
    setup = {"market": [["BUY_ANIMAL", "COW", 1], ["BUY_PRODUCT", "WHEAT", 1]]}
    cpu.step_market_only([setup for _ in seeds], [setup for _ in seeds])
    gpu.step_market_only([setup for _ in seeds], [setup for _ in seeds])

    build = {"farmer": ["BUILD_PASTURE"]}
    pickup = {"farmer": ["PICKUP", "COW", 1]}
    place = {"farmer": ["PLACE", "COW"]}
    pickup_wheat = {"farmer": ["PICKUP", "WHEAT", 1]}
    for action in [build, pickup, place, pickup_wheat]:
        for env_idx in range(len(seeds)):
            cpu._apply_unit_action(env_idx, 0, 0, action.get("farmer", ["PASS"]))
            cpu._apply_unit_action(env_idx, 1, 0, action.get("farmer", ["PASS"]))
        gpu.step_physical_slice([action for _ in seeds], [action for _ in seeds])

    for env_idx in range(len(seeds)):
        for player_idx in range(2):
            cpu.tiles[env_idx][player_idx][4][4]["fertilizer_available"] = True
            gpu.tiles[env_idx][player_idx][4][4]["fertilizer_available"] = True
            gpu._sync_physical_tensors(env_idx, player_idx)


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix first CUDA animal-action divergence before lifecycle or full-step work."
    return "3H-8E is closed for animal actions. Next port daily crop lifecycle, then daily animal lifecycle."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8E CUDA animal action audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_animal_action_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
