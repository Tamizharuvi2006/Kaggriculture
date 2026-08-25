"""Step 3H-8I CUDA terminal/reward semantics audit."""

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


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8I_TERMINAL_REWARD_AUDIT.json"
REWARD_NORMALIZER = CorrectedCudaPairedEngine.REWARD_NORMALIZER


def run_terminal_reward_audit(seeds: list[int], report_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    reports: list[dict[str, Any]] = []
    for case_name, step_idx, money_pair in _terminal_cases():
        cpu, gpu = _new_engines(seeds, device)
        _set_terminal_case(cpu, gpu, step_idx=step_idx, money_pair=money_pair)
        if gpu.actual_cuda_used:
            torch.cuda.synchronize(device)
        reports.append(_compare_case(case_name, cpu, gpu, seeds))

    failures = [
        seed_report
        for case in reports
        for seed_report in case["seed_reports"]
        if seed_report["status"] != "PASS"
    ]
    actual_cuda_used = all(case["actual_cuda_used"] for case in reports)
    unsupported_actions = 0
    report = {
        "status": "PASS" if not failures and actual_cuda_used and unsupported_actions == 0 else "FAIL",
        "step": "STEP 3H-8I - CUDA terminal/reward semantics",
        "scope": "terminal boundary, final cash/MCV, winner, raw terminal reward, and PPO-normalized reward only; full 719-step trajectory parity and benchmarking pending",
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(reports[0]["tensor_device"]) if reports else str(device),
        "actual_cuda_used": actual_cuda_used,
        "seeds_tested": len(seeds),
        "cases_tested": [case["case"] for case in reports],
        "unsupported_actions": unsupported_actions,
        "valuation_source": "corrected CPU reference uses terminal rewards = final cash/MCV; Step 5 normalizes reward delta by 100000.0",
        "reward_formula": "(our_MCV - opponent_MCV) / 100000.0 at terminal; 0.0 before terminal",
        "reports": reports,
        "timing_seconds": {"total_wall": round(time.perf_counter() - started, 6)},
        "recommendation": _recommendation(not failures and actual_cuda_used),
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


def _terminal_cases() -> list[tuple[str, int, tuple[float, float]]]:
    return [
        ("pre_terminal_boundary_reward_zero", 718, (91234.0, 81000.0)),
        ("terminal_p0_win", 719, (125500.0, 100250.0)),
        ("terminal_p1_win", 719, (74200.0, 111900.0)),
        ("terminal_tie", 719, (88000.0, 88000.0)),
        ("post_terminal_boundary_still_terminal", 720, (99000.0, 99001.0)),
    ]


def _set_terminal_case(
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    step_idx: int,
    money_pair: tuple[float, float],
) -> None:
    cpu.step_idx = int(step_idx)
    cpu.day_idx = int(step_idx // cpu.STEPS_PER_DAY)
    cpu.hour_idx = int(step_idx % cpu.STEPS_PER_DAY)
    gpu.step_idx = int(step_idx)
    gpu.day_idx = int(step_idx // gpu.STEPS_PER_DAY)
    gpu.hour_idx = int(step_idx % gpu.STEPS_PER_DAY)
    for env_idx in range(cpu.N):
        seed_offset = float(int(cpu.seeds[env_idx]) % 7)
        values = np.asarray([money_pair[0] + seed_offset, money_pair[1] + seed_offset], dtype=np.float64)
        cpu.money[env_idx] = values
        gpu.money[env_idx] = torch.tensor(values, dtype=torch.float64, device=gpu.device)


def _compare_case(
    case_name: str,
    cpu: CorrectedVectorPairedEngine,
    gpu: CorrectedCudaPairedEngine,
    seeds: list[int],
) -> dict[str, Any]:
    seed_reports = []
    for env_idx, seed in enumerate(seeds):
        perspective_reports = []
        for player_idx in (0, 1):
            cpu_metrics = _cpu_terminal_metrics(cpu, env_idx, player_idx)
            gpu_metrics = gpu.terminal_metrics(env_idx, player_idx)
            divergence = _compare_value(cpu_metrics, gpu_metrics, path="")
            perspective_reports.append(
                {
                    "player_idx": player_idx,
                    "status": "PASS" if divergence is None else "FAIL",
                    "divergence": divergence,
                    "cpu": cpu_metrics,
                    "cuda": gpu_metrics,
                }
            )
        seed_reports.append(
            {
                "seed": int(seed),
                "status": "PASS" if all(item["status"] == "PASS" for item in perspective_reports) else "FAIL",
                "perspectives": perspective_reports,
            }
        )
    return {
        "case": case_name,
        "status": "PASS" if all(item["status"] == "PASS" for item in seed_reports) else "FAIL",
        "tensor_device": str(gpu.money.device),
        "actual_cuda_used": bool(gpu.actual_cuda_used),
        "seed_reports": seed_reports,
    }


def _cpu_terminal_metrics(engine: CorrectedVectorPairedEngine, env_idx: int, player_idx: int) -> dict[str, Any]:
    opponent_idx = 1 - player_idx
    terminal_step = int(engine.config.terminal_step)
    terminal = int(engine.step_idx) >= terminal_step
    player_mcvs = [float(value) for value in np.asarray(engine.money[env_idx], dtype=np.float64).tolist()]
    own_mcv = player_mcvs[player_idx]
    opponent_mcv = player_mcvs[opponent_idx]
    raw_reward = own_mcv - opponent_mcv if terminal else 0.0
    winner = None if abs(player_mcvs[0] - player_mcvs[1]) <= 1e-9 else int(np.argmax(player_mcvs))
    return {
        "terminal": bool(terminal),
        "step": int(engine.step_idx),
        "terminal_step": terminal_step,
        "player_idx": int(player_idx),
        "our_mcv": own_mcv,
        "opponent_mcv": opponent_mcv,
        "player_mcvs": player_mcvs,
        "winner": winner,
        "raw_terminal_reward": float(raw_reward),
        "normalized_reward": float(raw_reward / REWARD_NORMALIZER),
        "reward_normalizer": REWARD_NORMALIZER,
        "valuation_source": "final_cash_matches_corrected_cpu_reference_and_existing_gpu_screeners",
    }


def _recommendation(passed: bool) -> str:
    if not passed:
        return "Fix CUDA terminal/reward divergence before full trajectory parity."
    return "3H-8I is closed for terminal/reward semantics. Next run full 719-step CUDA trajectory parity as a separate gate."


def _compare_value(left: Any, right: Any, path: str) -> dict[str, Any] | None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return {"path": path, "left_keys": sorted(left), "right_keys": sorted(right)}
        for key in sorted(left):
            child = _compare_value(left[key], right[key], f"{path}.{key}" if path else key)
            if child is not None:
                return child
        return None
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return {"path": path, "left_len": len(left), "right_len": len(right)}
        for idx, (left_item, right_item) in enumerate(zip(left, right)):
            child = _compare_value(left_item, right_item, f"{path}[{idx}]")
            if child is not None:
                return child
        return None
    if isinstance(left, float) or isinstance(right, float):
        if abs(float(left) - float(right)) > 1e-9:
            return {"path": path, "left": left, "right": right}
        return None
    if left != right:
        return {"path": path, "left": left, "right": right}
    return None


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8I CUDA terminal/reward semantics audit.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_terminal_reward_audit(_parse_seeds(args), report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
