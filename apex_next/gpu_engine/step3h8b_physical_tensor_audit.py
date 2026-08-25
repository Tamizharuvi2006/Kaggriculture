"""Step 3H-8B CUDA physical-state tensor mirror audit.

This gate does not claim full CUDA physical transitions. It proves that the
physical/private state needed for those transitions is now represented on CUDA
tensors and remains synchronized with the parity-correct CPU object state for
reset plus market-driven mutations.
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
from apex_next.gpu_engine.step3h_parity_audit import _compare_value, _run_real_kaggle  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8B_PHYSICAL_TENSOR_AUDIT.json"


def run_physical_tensor_audit(seeds: list[int], steps: int, report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    initial_reports = _compare_physical(cpu, gpu, seeds)
    traces = []
    trace_started = time.perf_counter()
    for seed in seeds:
        actions, _ = _run_real_kaggle(seed=seed, steps=steps)
        if len(actions) != steps:
            raise RuntimeError(f"Seed {seed} produced {len(actions)} actions, expected {steps}")
        traces.append(actions)
    trace_elapsed = time.perf_counter() - trace_started

    replay_started = time.perf_counter()
    for step_idx in range(steps):
        actions_p0 = [trace[step_idx]["p0"] for trace in traces]
        actions_p1 = [trace[step_idx]["p1"] for trace in traces]
        cpu.step_market_only(actions_p0, actions_p1)
        gpu.step_market_only(actions_p0, actions_p1)
    if gpu.actual_cuda_used:
        torch.cuda.synchronize(device)
    replay_elapsed = time.perf_counter() - replay_started

    final_reports = _compare_physical(cpu, gpu, seeds)
    initial_passed = sum(1 for item in initial_reports if item["status"] == "PASS")
    final_passed = sum(1 for item in final_reports if item["status"] == "PASS")
    status = "PASS" if initial_passed == len(seeds) and final_passed == len(seeds) and gpu.actual_cuda_used else "FAIL"
    report = {
        "status": status,
        "step": "STEP 3H-8B - CUDA physical-state tensor mirror",
        "scope": "CUDA-resident mirrors for tiles, hands, private shed, and seeds; physical action interpreter not CUDA-owned yet",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.tile_kind.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seeds_tested": len(seeds),
        "market_only_steps": steps,
        "initial_passed": initial_passed,
        "final_passed": final_passed,
        "initial_reports": initial_reports,
        "final_reports": final_reports,
        "timing_seconds": {
            "real_trace_collection": round(trace_elapsed, 6),
            "cpu_cuda_market_replay": round(replay_elapsed, 6),
            "total_wall": round(time.perf_counter() - started, 6),
        },
        "recommendation": _recommendation(status),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _compare_physical(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
) -> list[dict[str, Any]]:
    reports = []
    for env_idx, seed in enumerate(seeds):
        per_player = []
        for player_idx in range(2):
            expected = _object_physical_signature(cpu, env_idx, player_idx)
            actual = gpu.physical_tensor_signature(env_idx, player_idx)
            divergence = _compare_value(expected, actual, path="")
            per_player.append(
                {
                    "player": player_idx,
                    "status": "PASS" if divergence is None else "FAIL",
                    "cpu_vs_cuda_divergence": divergence,
                }
            )
        seed_status = "PASS" if all(item["status"] == "PASS" for item in per_player) else "FAIL"
        reports.append({"seed": seed, "status": seed_status, "players": per_player})
    return reports


def _object_physical_signature(engine: CorrectedVectorPairedEngine, env_idx: int, player_idx: int) -> dict[str, Any]:
    tile_counts = {str(value): 0 for value in range(0, CorrectedCudaPairedEngine.TILE_ANIMAL + 1)}
    tile_item_sum = 0
    tile_yield_sum = 0
    tile_flags_sum = 0
    for row in engine.tiles[env_idx][player_idx]:
        for tile in row:
            kind, item, yield_units, _planted_day, _placed_day, flags = _encode_tile(tile, engine.day_idx)
            tile_counts[str(kind)] += 1
            tile_item_sum += item
            tile_yield_sum += yield_units
            tile_flags_sum += flags

    shed = [
        int(engine.private_shed[env_idx][player_idx].get(item, 0))
        for item in CorrectedCudaPairedEngine.ITEM_INDEX
    ]
    seeds = [
        int(engine.seeds_private[env_idx][player_idx].get(crop, 0))
        for crop in CorrectedCudaPairedEngine.CROPS
    ]
    return {
        "tile_kind_counts": tile_counts,
        "tile_item_sum": tile_item_sum,
        "tile_yield_sum": tile_yield_sum,
        "tile_flags_sum": tile_flags_sum,
        "hand_count": len(engine.hands[env_idx][player_idx]),
        "hand_positions": [list(pos) for pos in engine.hands[env_idx][player_idx]],
        "shed": shed,
        "seeds": seeds,
        "devices": {
            "tile_kind": "cuda:0",
            "hand_pos": "cuda:0",
            "private_shed": "cuda:0",
            "seeds": "cuda:0",
        },
    }


def _encode_tile(tile: Any, day_idx: int) -> tuple[int, int, int, int, int, int]:
    if tile is None:
        return CorrectedCudaPairedEngine.TILE_EMPTY, 0, 0, -1, -1, 0
    if tile == "LOCKED":
        return CorrectedCudaPairedEngine.TILE_LOCKED, 0, 0, -1, -1, 0
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return CorrectedCudaPairedEngine.TILE_WEED, 0, 0, -1, -1, 0
    if isinstance(tile, dict) and tile.get("kind") == "PASTURE":
        return CorrectedCudaPairedEngine.TILE_PASTURE, 0, 0, -1, -1, 0
    if isinstance(tile, dict) and tile.get("kind") == "COOP":
        return CorrectedCudaPairedEngine.TILE_COOP, 0, 0, -1, -1, 0
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        flags = 0
        flags |= 1 if tile.get("watered_today", False) else 0
        flags |= 2 if tile.get("fertilized_until_day", -1) >= day_idx else 0
        return (
            CorrectedCudaPairedEngine.TILE_PLANT,
            CorrectedCudaPairedEngine.CROP_INDEX.get(tile.get("crop"), 0),
            int(tile.get("yield_units", 0)),
            int(tile.get("planted_day", -1)),
            -1,
            flags,
        )
    if isinstance(tile, dict) and "animal" in tile:
        flags = 0
        flags |= 1 if tile.get("fed_today", False) else 0
        flags |= 2 if tile.get("cared_today", False) else 0
        flags |= 4 if tile.get("fertilizer_available", False) else 0
        return (
            CorrectedCudaPairedEngine.TILE_ANIMAL,
            CorrectedCudaPairedEngine.ANIMAL_INDEX.get(tile.get("animal"), 0),
            int(tile.get("yield_units", 0)),
            -1,
            int(tile.get("placed_day", -1)),
            flags,
        )
    return CorrectedCudaPairedEngine.TILE_EMPTY, 0, 0, -1, -1, 0


def _recommendation(status: str) -> str:
    if status != "PASS":
        return "Fix the CUDA physical tensor mirror mismatch before porting physical actions."
    return "3H-8B is closed for physical-state mirrors. Next port movement and PICKUP/DROP/PLACE transitions to CUDA tensors."


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8B CUDA physical tensor mirror audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_physical_tensor_audit(_parse_seeds(args), steps=args.steps, report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
