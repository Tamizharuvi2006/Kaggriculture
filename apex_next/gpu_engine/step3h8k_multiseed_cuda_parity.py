"""Step 3H-8K multi-seed full CUDA trajectory parity audit."""

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
from apex_next.gpu_engine.step3h8j_full_cuda_trajectory_audit import (  # noqa: E402
    DEFAULT_TRACE_DIR,
    _compare_value,
    _cpu_terminal_metrics,
    _engine_projection,
    _load_or_create_trace,
)


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8K_20_SEED_CUDA_PARITY.json"
DEFAULT_STEP_LABEL = "STEP 3H-8K - 20-seed full CUDA trajectory parity"


def run_multiseed_cuda_parity(
    seeds: list[int],
    steps: int,
    report_path: Path,
    trace_dir: Path = DEFAULT_TRACE_DIR,
    collect_missing_trace: bool = True,
    per_seed_report_dir: Path | None = None,
    step_label: str = DEFAULT_STEP_LABEL,
) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    trace_started = time.perf_counter()
    traces = []
    for seed in seeds:
        traces.append(_load_or_create_trace(seed, steps, trace_dir, collect_missing_trace))
    trace_seconds = time.perf_counter() - trace_started

    cpu = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    gpu = CorrectedCudaPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0, device=device)
    cpu.reset(seeds)
    gpu.reset(seeds)

    seed_reports = [_initial_seed_summary(seed, trace) for seed, trace in zip(seeds, traces)]
    max_actions = max((len(trace["actions"]) for trace in traces), default=0)
    first_failure = None
    replay_started = time.perf_counter()
    for step_idx in range(1, max_actions + 1):
        action_batches_p0 = [trace["actions"][step_idx - 1]["p0"] for trace in traces]
        action_batches_p1 = [trace["actions"][step_idx - 1]["p1"] for trace in traces]
        cpu.step(action_batches_p0, action_batches_p1)
        gpu.step_integrated(action_batches_p0, action_batches_p1)

        numeric_divergence = _numeric_state_divergence(cpu, gpu)
        object_divergence = _object_state_divergence(cpu, gpu)
        tensor_divergence = _physical_tensor_divergence(gpu)
        for env_idx, seed in enumerate(seeds):
            report = seed_reports[env_idx]
            if report["status"] == "FAIL":
                continue
            report["cpu_steps_replayed"] = step_idx
            report["cuda_steps_replayed"] = step_idx
            divergence = _seed_divergence(numeric_divergence, object_divergence, env_idx)
            if divergence is not None:
                divergence["step"] = step_idx
                divergence["detail"] = _detailed_projection_divergence(cpu, gpu, env_idx)
                report["first_divergence"] = divergence
            physical = _seed_physical_divergence(tensor_divergence, env_idx)
            if physical is not None:
                report["tensor_object_divergence"] = {"step": step_idx, "physical": physical}
            if report["first_divergence"] is not None or report["tensor_object_divergence"] is not None:
                report["status"] = "FAIL"
                if first_failure is None:
                    first_failure = report
        if first_failure is not None:
            break

    replay_seconds = time.perf_counter() - replay_started
    terminal_started = time.perf_counter()
    final_physical_reports = _compare_all(cpu, gpu, seeds)
    for env_idx, seed in enumerate(seeds):
        report = seed_reports[env_idx]
        terminal_cpu = _cpu_terminal_metrics(cpu, env_idx, 0)
        terminal_cuda = gpu.terminal_metrics(env_idx, 0)
        terminal_divergence = _compare_value(terminal_cpu, terminal_cuda, path="")
        final_physical = final_physical_reports[env_idx]
        report["terminal_cpu"] = terminal_cpu
        report["terminal_cuda"] = terminal_cuda
        report["terminal_divergence"] = terminal_divergence
        report["final_physical"] = final_physical
        report["actual_cuda_used"] = bool(gpu.actual_cuda_used)
        report["tensor_device"] = str(gpu.money.device)
        report["cuda_device_name"] = device_name
        if terminal_divergence is not None or final_physical["status"] != "PASS":
            report["status"] = "FAIL"
        if not _seed_acceptance(report):
            report["status"] = "FAIL"
        if report["status"] != "PASS" and first_failure is None:
            first_failure = report
        print(
            f"seed={seed} status={report['status']} "
            f"real={report['real_steps_recorded']} "
            f"cpu={report['cpu_steps_replayed']} "
            f"cuda={report['cuda_steps_replayed']} "
            f"first_divergence={report['first_divergence']} "
            f"tensor_object_divergence={report['tensor_object_divergence']} "
            f"terminal_divergence={report['terminal_divergence']} "
            f"unsupported={report['unsupported_or_ignored_entries']} "
            f"cuda={report['actual_cuda_used']}",
            flush=True,
        )
    terminal_seconds = time.perf_counter() - terminal_started

    passed = [item for item in seed_reports if item["status"] == "PASS"]
    failures = [item for item in seed_reports if item["status"] != "PASS"]
    report = {
        "status": "PASS" if len(passed) == len(seed_reports) else "FAIL",
        "step": step_label,
        "scope": "multi-seed full deterministic CUDA replay; no performance benchmark and no Step 5B rollout",
        "steps_requested": steps,
        "required_transitions": 719,
        "trace_dir": str(trace_dir),
        "trace_sources": {
            "cached": sum(1 for trace in traces if trace["trace_source"] == "cached_real_kaggle_action_trace"),
            "created_this_run": sum(1 for trace in traces if trace["created_this_run"]),
        },
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.money.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seeds_tested": len(seed_reports),
        "seeds_passed": len(passed),
        "seeds_failed": len(failures),
        "pass_rate": 0.0 if not seed_reports else len(passed) / len(seed_reports),
        "first_failure": failures[0] if failures else first_failure,
        "seed_reports": seed_reports,
        "acceptance": {
            "all_real_steps_719": all(item["real_steps_recorded"] == 719 for item in seed_reports),
            "all_cpu_steps_719": all(item["cpu_steps_replayed"] == 719 for item in seed_reports),
            "all_cuda_steps_719": all(item["cuda_steps_replayed"] == 719 for item in seed_reports),
            "all_first_divergence_null": all(item["first_divergence"] is None for item in seed_reports),
            "all_tensor_object_divergence_null": all(item["tensor_object_divergence"] is None for item in seed_reports),
            "all_terminal_divergence_null": all(item["terminal_divergence"] is None for item in seed_reports),
            "all_unsupported_zero": all(item["unsupported_or_ignored_entries"] == 0 for item in seed_reports),
            "all_actual_cuda_used": all(item["actual_cuda_used"] is True for item in seed_reports),
            "all_tensor_device_cuda0": all(item["tensor_device"] == "cuda:0" for item in seed_reports),
            "all_exceptions_zero": all(item["error"] is None for item in seed_reports),
        },
        "timing_seconds": {
            "trace_load_or_create": round(trace_seconds, 6),
            "batched_cpu_cuda_replay": round(replay_seconds, 6),
            "terminal_finalize": round(terminal_seconds, 6),
            "total_wall": round(time.perf_counter() - started, 6),
        },
        "recommendation": _recommendation(failures),
    }
    if per_seed_report_dir is not None:
        per_seed_report_dir.mkdir(parents=True, exist_ok=True)
        for seed_report in seed_reports:
            seed_report_path = per_seed_report_dir / f"SEED_{seed_report['seed']}.json"
            seed_report_path.write_text(json.dumps(seed_report, indent=2), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _initial_seed_summary(seed: int, trace: dict[str, Any]) -> dict[str, Any]:
    unsupported = trace.get("unsupported_actions") or {}
    return {
        "seed": seed,
        "status": "PASS" if trace["real_vs_paired_reference_divergence"] is None else "FAIL",
        "trace_source": trace.get("trace_source"),
        "trace_path": trace.get("trace_path"),
        "trace_created_this_run": trace.get("created_this_run"),
        "real_steps_recorded": trace.get("real_steps_recorded"),
        "cpu_steps_replayed": 0,
        "cuda_steps_replayed": 0,
        "real_vs_paired_reference_divergence": trace.get("real_vs_paired_reference_divergence"),
        "first_divergence": None,
        "tensor_object_divergence": None,
        "terminal_divergence": None,
        "unsupported_or_ignored_entries": unsupported.get("unsupported_or_ignored_entries"),
        "unsupported_or_ignored_commands": unsupported.get("unsupported_or_ignored_commands"),
        "actual_cuda_used": False,
        "tensor_device": None,
        "cuda_device_name": None,
        "terminal_cpu": None,
        "terminal_cuda": None,
        "final_physical": None,
        "error": None,
    }


def _numeric_state_divergence(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
) -> dict[str, Any] | None:
    scalar_pairs = {
        "step_idx": (cpu.step_idx, gpu.step_idx),
        "day_idx": (cpu.day_idx, gpu.day_idx),
        "hour_idx": (cpu.hour_idx, gpu.hour_idx),
    }
    for name, (left, right) in scalar_pairs.items():
        if int(left) != int(right):
            return {"kind": "numeric", "field": name, "left": int(left), "right": int(right)}

    checks = [
        ("money", cpu.money, gpu.money, True),
        ("land_count", cpu.land_count, gpu.land_count, False),
        ("workers", cpu.workers, gpu.workers, False),
        ("hires_today", cpu.hires_today, gpu.hires_today, False),
        ("active_cows", cpu.active_cows, gpu.active_cows, False),
        ("active_sheep", cpu.active_sheep, gpu.active_sheep, False),
        ("plant_tiles", cpu.plant_tiles, gpu.plant_tiles, False),
        ("animal_tiles", cpu.animal_tiles, gpu.animal_tiles, False),
        ("farmers", cpu.farmers, gpu.farmers, False),
        ("public_inventory", cpu.public_inventory, gpu.public_inventory, True),
        ("market_inventory", cpu.market_inventory, gpu.market_inventory, False),
        ("market_prices", cpu.market_prices, gpu.market_prices, True),
    ]
    for name, expected, actual, is_float in checks:
        expected_tensor = torch.as_tensor(expected, dtype=actual.dtype, device=actual.device)
        if is_float:
            equal = torch.allclose(expected_tensor, actual, atol=1e-6, rtol=0.0)
        else:
            equal = torch.equal(expected_tensor, actual)
        if not bool(equal.item() if hasattr(equal, "item") else equal):
            return {"kind": "numeric", "field": name}
    return None


def _object_state_divergence(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
) -> dict[str, Any] | None:
    fields = [
        "hands",
        "unlocked_quadrants",
        "tiles",
        "private_shed",
        "private_inventories",
        "seeds_private",
        "town_shops",
    ]
    for field in fields:
        left = getattr(cpu, field)
        right = getattr(gpu, field)
        if left != right:
            return {"kind": "object", "field": field, "detail": _compare_value(left, right, path=field)}
    return None


def _physical_tensor_divergence(gpu: CorrectedCudaPairedEngine) -> dict[str, Any] | None:
    expected = _expected_physical_tensors(gpu)
    checks = [
        ("tile_kind", expected["tile_kind"], gpu.tile_kind),
        ("tile_item", expected["tile_item"], gpu.tile_item),
        ("tile_yield", expected["tile_yield"], gpu.tile_yield),
        ("tile_planted_day", expected["tile_planted_day"], gpu.tile_planted_day),
        ("tile_placed_day", expected["tile_placed_day"], gpu.tile_placed_day),
        ("tile_flags", expected["tile_flags"], gpu.tile_flags),
        ("hand_active", expected["hand_active"], gpu.hand_active),
        ("hand_pos", expected["hand_pos"], gpu.hand_pos),
        ("private_shed_tensor", expected["private_shed_tensor"], gpu.private_shed_tensor),
        ("seed_tensor", expected["seed_tensor"], gpu.seed_tensor),
    ]
    for name, expected_array, actual in checks:
        expected_tensor = torch.as_tensor(expected_array, dtype=actual.dtype, device=actual.device)
        equal = torch.equal(expected_tensor, actual)
        if not bool(equal.item() if hasattr(equal, "item") else equal):
            return {"kind": "tensor", "field": name}
    return None


def _expected_physical_tensors(gpu: CorrectedCudaPairedEngine) -> dict[str, np.ndarray]:
    n = gpu.N
    board = gpu.BOARD_SIZE
    max_hands = gpu.MAX_HANDS
    tile_kind = np.zeros((n, 2, board, board), dtype=np.int16)
    tile_item = np.zeros((n, 2, board, board), dtype=np.int16)
    tile_yield = np.zeros((n, 2, board, board), dtype=np.int16)
    tile_planted_day = np.full((n, 2, board, board), -1, dtype=np.int16)
    tile_placed_day = np.full((n, 2, board, board), -1, dtype=np.int16)
    tile_flags = np.zeros((n, 2, board, board), dtype=np.int16)
    hand_active = np.zeros((n, 2, max_hands), dtype=np.bool_)
    hand_pos = np.full((n, 2, max_hands, 2), -1, dtype=np.int16)
    private_shed_tensor = np.zeros((n, 2, len(gpu.ITEM_INDEX)), dtype=np.int16)
    seed_tensor = np.zeros((n, 2, len(gpu.CROPS)), dtype=np.int16)

    for env_idx in range(n):
        for player_idx in range(2):
            for y, row in enumerate(gpu.tiles[env_idx][player_idx]):
                for x, tile in enumerate(row):
                    kind, item, yield_units, planted_day, placed_day, flags = gpu._encode_tile(tile)
                    tile_kind[env_idx, player_idx, y, x] = kind
                    tile_item[env_idx, player_idx, y, x] = item
                    tile_yield[env_idx, player_idx, y, x] = yield_units
                    tile_planted_day[env_idx, player_idx, y, x] = planted_day
                    tile_placed_day[env_idx, player_idx, y, x] = placed_day
                    tile_flags[env_idx, player_idx, y, x] = flags
            for hand_idx, pos in enumerate(gpu.hands[env_idx][player_idx][:max_hands]):
                hand_active[env_idx, player_idx, hand_idx] = True
                hand_pos[env_idx, player_idx, hand_idx] = pos
            for item, count in gpu.private_shed[env_idx][player_idx].items():
                item_idx = gpu.ITEM_INDEX.get(item)
                if item_idx is not None:
                    private_shed_tensor[env_idx, player_idx, item_idx] = int(count)
            for crop_idx, crop in enumerate(gpu.CROPS):
                seed_tensor[env_idx, player_idx, crop_idx] = int(gpu.seeds_private[env_idx][player_idx].get(crop, 0))

    return {
        "tile_kind": tile_kind,
        "tile_item": tile_item,
        "tile_yield": tile_yield,
        "tile_planted_day": tile_planted_day,
        "tile_placed_day": tile_placed_day,
        "tile_flags": tile_flags,
        "hand_active": hand_active,
        "hand_pos": hand_pos,
        "private_shed_tensor": private_shed_tensor,
        "seed_tensor": seed_tensor,
    }


def _seed_divergence(
    numeric_divergence: dict[str, Any] | None,
    object_divergence: dict[str, Any] | None,
    env_idx: int,
) -> dict[str, Any] | None:
    if numeric_divergence is not None:
        return {**numeric_divergence, "env_idx": env_idx}
    if object_divergence is not None:
        return {**object_divergence, "env_idx": env_idx}
    return None


def _seed_physical_divergence(tensor_divergence: dict[str, Any] | None, env_idx: int) -> dict[str, Any] | None:
    if tensor_divergence is None:
        return None
    return {
        "status": "FAIL",
        "seed_index": env_idx,
        "players": [],
        "fast_tensor_divergence": {**tensor_divergence, "env_idx": env_idx},
    }


def _detailed_projection_divergence(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    env_idx: int,
) -> dict[str, Any] | None:
    cpu_snapshot = _engine_projection(cpu, env_idx)
    gpu_snapshot = _engine_projection(gpu, env_idx)
    return _compare_value(cpu_snapshot, gpu_snapshot, path="")


def _seed_acceptance(report: dict[str, Any]) -> bool:
    return (
        report["real_vs_paired_reference_divergence"] is None
        and report["first_divergence"] is None
        and report["tensor_object_divergence"] is None
        and report["terminal_divergence"] is None
        and report["unsupported_or_ignored_entries"] == 0
        and report["real_steps_recorded"] == 719
        and report["cpu_steps_replayed"] == 719
        and report["cuda_steps_replayed"] == 719
        and report["actual_cuda_used"] is True
        and report["tensor_device"] == "cuda:0"
        and report["error"] is None
    )


def _recommendation(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return "3H-8K is closed for 20-seed full CUDA parity. Next gate is 100-seed full CUDA parity; still no benchmark or Step 5B."
    first = failures[0]
    return (
        f"Do not advance to 100-seed parity or benchmarking. First failing seed is {first['seed']} "
        f"with first_divergence={first['first_divergence']}, "
        f"tensor_object_divergence={first['tensor_object_divergence']}, "
        f"terminal_divergence={first['terminal_divergence']}, error={first['error']}."
    )


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8K multi-seed full CUDA parity audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--no-collect-missing-trace", action="store_true")
    parser.add_argument("--per-seed-report-dir", type=Path, default=None)
    parser.add_argument("--step-label", type=str, default=DEFAULT_STEP_LABEL)
    args = parser.parse_args()
    report = run_multiseed_cuda_parity(
        _parse_seeds(args),
        steps=args.steps,
        report_path=args.report,
        trace_dir=args.trace_dir,
        collect_missing_trace=not args.no_collect_missing_trace,
        per_seed_report_dir=args.per_seed_report_dir,
        step_label=args.step_label,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
