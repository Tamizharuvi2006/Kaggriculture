"""Step 3H-8J full CUDA trajectory parity audit."""

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
from apex_next.gpu_engine.step3h_parity_audit import (  # noqa: E402
    _first_divergence,
    _replay_in_paired_sim,
    _run_real_kaggle,
    _unsupported_action_summary,
)
from apex_next.gpu_engine.step3h7_vector_port_audit import _projection, _projection_from_sim_snapshot, _snapshot_sim  # noqa: E402
from apex_next.gpu_engine.step3h8c_physical_slice_audit import _compare_all  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "cuda" / "STEP3H8J_FULL_CUDA_TRAJECTORY_AUDIT.json"
DEFAULT_TRACE_DIR = PROJECT_ROOT / "reports" / "step3h" / "traces" / "step3h_real_action_traces"
LEGACY_TRACE_DIR = PROJECT_ROOT / "reports" / "step3h_real_action_traces"


def run_full_cuda_trajectory_audit(
    seed: int,
    steps: int,
    report_path: Path,
    trace_dir: Path = DEFAULT_TRACE_DIR,
    collect_missing_trace: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    trace_started = time.perf_counter()
    trace = _load_or_create_trace(seed, steps, trace_dir, collect_missing_trace)
    trace_seconds = time.perf_counter() - trace_started
    actions = trace["actions"]
    real_vs_paired = trace["real_vs_paired_reference_divergence"]
    unsupported = trace["unsupported_actions"]
    real_steps = trace["real_steps_recorded"]

    cpu = CorrectedVectorPairedEngine(batch_size=1, base_seed=seed)
    gpu = CorrectedCudaPairedEngine(batch_size=1, base_seed=seed, device=device)
    cpu.reset([seed])
    gpu.reset([seed])

    cpu_snapshots = [_engine_projection(cpu, 0)]
    gpu_snapshots = [_engine_projection(gpu, 0)]
    first_cpu_cuda_divergence = _compare_value(cpu_snapshots[0], gpu_snapshots[0], path="")
    first_tensor_object_divergence = None
    exception = None

    if first_cpu_cuda_divergence is None:
        try:
            for step_idx, action_pair in enumerate(actions, start=1):
                cpu.step([action_pair["p0"]], [action_pair["p1"]])
                gpu.step_integrated([action_pair["p0"]], [action_pair["p1"]])
                if gpu.actual_cuda_used:
                    torch.cuda.synchronize(device)
                cpu_snapshot = _engine_projection(cpu, 0)
                gpu_snapshot = _engine_projection(gpu, 0)
                cpu_snapshots.append(cpu_snapshot)
                gpu_snapshots.append(gpu_snapshot)
                divergence = _compare_value(cpu_snapshot, gpu_snapshot, path="")
                if divergence is not None:
                    divergence["step"] = step_idx
                    first_cpu_cuda_divergence = divergence
                    break
                physical = _compare_all(cpu, gpu, [seed])[0]
                if physical["status"] != "PASS":
                    first_tensor_object_divergence = {"step": step_idx, "physical": physical}
                    break
        except Exception as exc:  # pragma: no cover - diagnostic report path
            exception = f"{type(exc).__name__}: {exc}"

    terminal_cpu = _cpu_terminal_metrics(cpu, 0, 0)
    terminal_cuda = gpu.terminal_metrics(0, 0)
    terminal_divergence = _compare_value(terminal_cpu, terminal_cuda, path="")
    final_physical = _compare_all(cpu, gpu, [seed])[0] if exception is None else None
    actual_cuda_used = bool(gpu.actual_cuda_used)

    cpu_steps = len(cpu_snapshots) - 1
    cuda_steps = len(gpu_snapshots) - 1
    passed = (
        exception is None
        and real_vs_paired is None
        and first_cpu_cuda_divergence is None
        and first_tensor_object_divergence is None
        and terminal_divergence is None
        and final_physical is not None
        and final_physical["status"] == "PASS"
        and unsupported["unsupported_or_ignored_entries"] == 0
        and real_steps == 719
        and cpu_steps == 719
        and cuda_steps == 719
        and actual_cuda_used
    )
    report = {
        "status": "PASS" if passed else "FAIL",
        "step": "STEP 3H-8J - Full 719-step CUDA trajectory parity",
        "scope": "single-seed full deterministic replay; no CUDA performance benchmark and no Step 5B rollout",
        "seed": seed,
        "trace_source": trace["trace_source"],
        "trace_path": trace["trace_path"],
        "trace_created_this_run": trace["created_this_run"],
        "steps_requested": steps,
        "required_transitions": 719,
        "real_steps_recorded": real_steps,
        "cpu_steps_replayed": cpu_steps,
        "cuda_steps_replayed": cuda_steps,
        "cuda_available": cuda_available,
        "cuda_device_name": device_name,
        "tensor_device": str(gpu.money.device),
        "actual_cuda_used": actual_cuda_used,
        "unsupported_actions": unsupported,
        "real_vs_paired_reference_divergence": real_vs_paired,
        "first_divergence": first_cpu_cuda_divergence,
        "tensor_object_divergence": first_tensor_object_divergence,
        "terminal_divergence": terminal_divergence,
        "terminal_cpu": terminal_cpu,
        "terminal_cuda": terminal_cuda,
        "final_physical": final_physical,
        "exception": exception,
        "acceptance": {
            "real_paired_reference_parity": real_vs_paired is None,
            "cpu_cuda_first_divergence_null": first_cpu_cuda_divergence is None,
            "tensor_object_divergence_null": first_tensor_object_divergence is None and final_physical is not None and final_physical["status"] == "PASS",
            "terminal_reward_identical": terminal_divergence is None,
            "unsupported_actions_zero": unsupported["unsupported_or_ignored_entries"] == 0,
            "all_transition_counts_719": real_steps == 719 and cpu_steps == 719 and cuda_steps == 719,
            "actual_cuda_used": actual_cuda_used,
        },
        "timing_seconds": {
            "trace_load_or_create": round(trace_seconds, 6),
            "total_wall": round(time.perf_counter() - started, 6),
        },
        "recommendation": _recommendation(passed, first_cpu_cuda_divergence, terminal_divergence, exception),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _load_or_create_trace(seed: int, steps: int, trace_dir: Path, collect_missing_trace: bool) -> dict[str, Any]:
    trace_path = trace_dir / f"real_action_trace_seed_{seed}_steps_{steps}.json"
    legacy_trace_path = LEGACY_TRACE_DIR / trace_path.name
    if trace_path.exists():
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
        return {
            "trace_source": "cached_real_kaggle_action_trace",
            "trace_path": str(trace_path),
            "created_this_run": False,
            "actions": payload["actions"],
            "real_steps_recorded": payload["real_steps_recorded"],
            "real_vs_paired_reference_divergence": payload["real_vs_paired_reference_divergence"],
            "unsupported_actions": payload["unsupported_actions"],
        }
    if trace_dir == DEFAULT_TRACE_DIR and legacy_trace_path.exists():
        payload = json.loads(legacy_trace_path.read_text(encoding="utf-8"))
        return {
            "trace_source": "cached_legacy_real_kaggle_action_trace",
            "trace_path": str(legacy_trace_path),
            "created_this_run": False,
            "actions": payload["actions"],
            "real_steps_recorded": payload["real_steps_recorded"],
            "real_vs_paired_reference_divergence": payload["real_vs_paired_reference_divergence"],
            "unsupported_actions": payload["unsupported_actions"],
        }
    if not collect_missing_trace:
        raise FileNotFoundError(f"Missing cached real action trace: {trace_path}")

    actions, real_snapshots = _run_real_kaggle(seed=seed, steps=steps)
    paired_snapshots = _replay_in_paired_sim(seed=seed, actions=actions)
    real_vs_paired = _first_divergence(real_snapshots, paired_snapshots)
    unsupported = _unsupported_action_summary(actions)
    payload = {
        "schema": "STEP3H_REAL_ACTION_TRACE_V1",
        "seed": seed,
        "steps_requested": steps,
        "real_steps_recorded": len(real_snapshots) - 1,
        "paired_steps_replayed": len(paired_snapshots) - 1,
        "real_vs_paired_reference_divergence": real_vs_paired,
        "unsupported_actions": unsupported,
        "actions": actions,
    }
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "trace_source": "new_real_kaggle_action_trace",
        "trace_path": str(trace_path),
        "created_this_run": True,
        "actions": actions,
        "real_steps_recorded": payload["real_steps_recorded"],
        "real_vs_paired_reference_divergence": real_vs_paired,
        "unsupported_actions": unsupported,
    }


def _engine_projection(engine: Any, env_idx: int) -> dict[str, Any]:
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


def _cpu_terminal_metrics(engine: CorrectedVectorPairedEngine, env_idx: int, player_idx: int) -> dict[str, Any]:
    opponent_idx = 1 - player_idx
    terminal_step = int(engine.config.terminal_step)
    terminal = int(engine.step_idx) >= terminal_step
    player_mcvs = [float(value) for value in engine.money[env_idx].tolist()]
    own_mcv = player_mcvs[player_idx]
    opponent_mcv = player_mcvs[opponent_idx]
    raw_reward = own_mcv - opponent_mcv if terminal else 0.0
    winner = None if abs(player_mcvs[0] - player_mcvs[1]) <= 1e-9 else int(0 if player_mcvs[0] > player_mcvs[1] else 1)
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
        "normalized_reward": float(raw_reward / CorrectedCudaPairedEngine.REWARD_NORMALIZER),
        "reward_normalizer": CorrectedCudaPairedEngine.REWARD_NORMALIZER,
        "valuation_source": "final_cash_matches_corrected_cpu_reference_and_existing_gpu_screeners",
    }


def _compare_value(left: Any, right: Any, path: str) -> dict[str, Any] | None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return {"field": path, "left_keys": sorted(left), "right_keys": sorted(right)}
        for key in sorted(left):
            child = _compare_value(left[key], right[key], f"{path}.{key}" if path else key)
            if child is not None:
                return child
        return None
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return {"field": path, "left": left, "right": right}
        for idx, (left_item, right_item) in enumerate(zip(left, right)):
            child = _compare_value(left_item, right_item, f"{path}[{idx}]")
            if child is not None:
                return child
        return None
    if isinstance(left, float) or isinstance(right, float):
        if abs(float(left) - float(right)) > 1e-6:
            return {"field": path, "left": left, "right": right}
        return None
    if left != right:
        return {"field": path, "left": left, "right": right}
    return None


def _recommendation(
    passed: bool,
    first_divergence: dict[str, Any] | None,
    terminal_divergence: dict[str, Any] | None,
    exception: str | None,
) -> str:
    if passed:
        return "3H-8J is closed for one full CUDA trajectory. Next gate is 20-seed full CUDA parity; no benchmark yet."
    if exception is not None:
        return f"Fix CUDA trajectory exception before expanding parity: {exception}"
    if first_divergence is not None:
        return f"Fix first CPU/CUDA trajectory divergence before 20-seed parity: {first_divergence}"
    if terminal_divergence is not None:
        return f"Fix terminal/reward divergence before 20-seed parity: {terminal_divergence}"
    return "Do not advance. Fix failed 3H-8J acceptance item before multi-seed CUDA parity."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-8J full CUDA trajectory parity audit.")
    parser.add_argument("--seed", type=int, default=39000)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--no-collect-missing-trace", action="store_true")
    args = parser.parse_args()
    report = run_full_cuda_trajectory_audit(
        seed=args.seed,
        steps=args.steps,
        report_path=args.report,
        trace_dir=args.trace_dir,
        collect_missing_trace=not args.no_collect_missing_trace,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
