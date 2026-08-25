"""Collect real APEX 4.0 expert demonstrations for Step 2.

This collector executes the sealed APEX4_SUBMISSION_FINAL.py as the expert
policy inside kaggle_environments. It does not modify production or sealed
agent files.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import multiprocessing as mp
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import KaggricultureGymEnv, call_agent, load_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import FEATURE_DIM, opponent_features, extract_features
from apex_next.ml_engine.training.targeted_opponents import (
    aggressive_expand_agent,
    crop_heavy_agent,
    market_manipulator_agent,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PILOT_DIR = DATA_DIR / "pilots" / "step2_pilot"
BENCHMARK_DIR = DATA_DIR / "benchmarks" / "parallel"
DEFAULT_OUTPUT = PILOT_DIR / "expert_demos_pilot_10.npz"
DEFAULT_REPORT = PILOT_DIR / "expert_demos_pilot_10_report.json"
APEX4_PATH = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
APEX35_PATH = PROJECT_ROOT / "submission.py"
V18_PATH = PROJECT_ROOT / "baseline" / "kaitofukami-v18.py"
DEFAULT_OLD_MODEL_PATH = PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_apex30.py"

AgentFn = Callable[[dict[str, Any], Any], dict[str, list[Any]]]


def collect_expert_demos(
    episodes: int = 10,
    seed_start: int = 2000,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    episode_offset: int = 0,
    include_old_model: bool = False,
    include_targeted_archetypes: bool = False,
    old_model_path: Path = DEFAULT_OLD_MODEL_PATH,
) -> dict[str, Any]:
    """Collect expert transitions and write a reloadable NPZ plus JSON report."""

    started = time.perf_counter()
    expert_agent = load_agent(APEX4_PATH)
    opponent_pool = _opponent_pool(
        include_old_model=include_old_model,
        include_targeted_archetypes=include_targeted_archetypes,
        old_model_path=old_model_path,
    )

    features_rows: list[np.ndarray] = []
    opponent_feature_rows: list[np.ndarray] = []
    raw_action_json_rows: list[str] = []
    action_json_rows: list[str] = []
    raw_opponent_action_json_rows: list[str] = []
    opponent_action_json_rows: list[str] = []
    reward_rows: list[float] = []
    terminal_rows: list[bool] = []
    episode_id_rows: list[int] = []
    step_rows: list[int] = []
    opponent_id_rows: list[str] = []
    sanitized_changed = 0
    raw_market_over_cap = 0
    episode_reports = []
    exceptions: list[dict[str, Any]] = []

    for local_episode_index in range(episodes):
        episode_index = episode_offset + local_episode_index
        seed = seed_start + episode_index
        opponent_id, opponent_fn = opponent_pool[episode_index % len(opponent_pool)]
        env = KaggricultureGymEnv(opponent_fn=opponent_fn)
        episode_started = time.perf_counter()
        report: dict[str, Any] = {
            "episode": episode_index,
            "seed": seed,
            "opponent_id": opponent_id,
            "completed": False,
            "steps": 0,
            "terminal_reward": None,
            "exception": None,
            "sanitized_action_changes": 0,
        }

        try:
            env.reset(seed=seed)
            done = False
            while not done:
                if env.state is None:
                    raise AssertionError("environment state unexpectedly missing")

                obs = _observation(env.state[0])
                features = extract_features(obs)
                _validate_features(features)

                raw_action = call_agent(expert_agent, obs, env.env.configuration)
                action = sanitize_action(raw_action)
                raw_market_len = len(raw_action.get("market", [])) if isinstance(raw_action, dict) else 0
                if raw_market_len > 10:
                    raw_market_over_cap += 1
                if action != _json_roundtrip(raw_action):
                    sanitized_changed += 1
                    report["sanitized_action_changes"] += 1
                _validate_action(action)

                next_features, reward, done, info = env.step(action)
                _validate_features(next_features)
                _validate_action(info["our_action"])
                _validate_action(info["opponent_action"])

                features_rows.append(features)
                opponent_feature_rows.append(opponent_features(features))
                raw_action_json_rows.append(json.dumps(raw_action, sort_keys=True, separators=(",", ":")))
                action_json_rows.append(json.dumps(action, sort_keys=True, separators=(",", ":")))
                raw_opponent_action_json_rows.append(
                    json.dumps(info["raw_opponent_action"], sort_keys=True, separators=(",", ":"))
                )
                opponent_action_json_rows.append(
                    json.dumps(info["opponent_action"], sort_keys=True, separators=(",", ":"))
                )
                reward_rows.append(float(reward))
                terminal_rows.append(bool(done))
                episode_id_rows.append(episode_index)
                step_rows.append(int(info["step"]))
                opponent_id_rows.append(opponent_id)
                report["steps"] = int(info["step"])

                if report["steps"] > 720:
                    raise AssertionError(f"episode exceeded 720 steps: {report['steps']}")

            report["completed"] = True
            report["terminal_reward"] = float(reward_rows[-1]) if reward_rows else 0.0
        except Exception as exc:  # noqa: BLE001 - report exact pilot failure.
            report["exception"] = repr(exc)
            exceptions.append({"episode": episode_index, "seed": seed, "exception": repr(exc)})

        report["elapsed_seconds"] = round(time.perf_counter() - episode_started, 6)
        episode_reports.append(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        features=np.asarray(features_rows, dtype=np.float32),
        opponent_features=np.asarray(opponent_feature_rows, dtype=np.float32),
        raw_actions_json=_bytes_array(raw_action_json_rows),
        actions_json=_bytes_array(action_json_rows),
        raw_opponent_actions_json=_bytes_array(raw_opponent_action_json_rows),
        opponent_actions_json=_bytes_array(opponent_action_json_rows),
        rewards=np.asarray(reward_rows, dtype=np.float32),
        terminals=np.asarray(terminal_rows, dtype=np.bool_),
        episode_ids=np.asarray(episode_id_rows, dtype=np.int32),
        steps=np.asarray(step_rows, dtype=np.int16),
        opponent_ids=_bytes_array(opponent_id_rows),
    )

    validation = validate_dataset(output_path)
    summary = {
        "status": "PASS" if not exceptions and validation["status"] == "PASS" else "FAIL",
        "episodes_requested": episodes,
        "episodes_completed": sum(1 for ep in episode_reports if ep["completed"]),
        "episode_offset": episode_offset,
        "total_transitions": len(features_rows),
        "observed_step_counts": [ep["steps"] for ep in episode_reports],
        "terminal_rewards": [ep["terminal_reward"] for ep in episode_reports],
        "exceptions": exceptions,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "expert_policy": str(APEX4_PATH),
        "opponent_cycle": [opponent_id for opponent_id, _ in opponent_pool],
        "output_path": str(output_path),
        "sanitized_action_changes": sanitized_changed,
        "raw_market_over_cap": raw_market_over_cap,
        "validation": validation,
        "episodes": episode_reports,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def collect_expert_demos_parallel(
    episodes: int,
    seed_start: int,
    workers: int,
    output_path: Path,
    report_path: Path,
    expected_transitions: int | None = None,
    include_old_model: bool = False,
    include_targeted_archetypes: bool = False,
    old_model_path: Path = DEFAULT_OLD_MODEL_PATH,
) -> dict[str, Any]:
    """Collect demonstrations in isolated worker processes and merge shards."""

    started = time.perf_counter()
    workers = max(1, int(workers))
    if workers == 1:
        summary = collect_expert_demos(
            episodes=episodes,
            seed_start=seed_start,
            output_path=output_path,
            report_path=report_path,
            episode_offset=0,
            include_old_model=include_old_model,
            include_targeted_archetypes=include_targeted_archetypes,
            old_model_path=old_model_path,
        )
        _enforce_collection_contract(summary, episodes, expected_transitions)
        return summary

    shard_dir = output_path.parent / f"{output_path.stem}_shards"
    if shard_dir.exists():
        shutil.rmtree(shard_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)

    shards = _episode_shards(episodes, workers)
    tasks = []
    for shard_index, (offset, count) in enumerate(shards):
        if count <= 0:
            continue
        tasks.append(
            {
                "shard_index": shard_index,
                "episodes": count,
                "seed_start": seed_start,
                "episode_offset": offset,
                "output_path": shard_dir / f"shard_{shard_index:03d}.npz",
                "report_path": shard_dir / f"shard_{shard_index:03d}_report.json",
                "include_old_model": include_old_model,
                "include_targeted_archetypes": include_targeted_archetypes,
                "old_model_path": old_model_path,
            }
        )

    context = mp.get_context("spawn")
    shard_summaries = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        future_to_task = {executor.submit(_collect_shard, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                shard_summaries.append(future.result())
            except Exception as exc:  # noqa: BLE001 - benchmark/report worker failures.
                shard_summaries.append(
                    {
                        "status": "FAIL",
                        "episodes_requested": int(task["episodes"]),
                        "episodes_completed": 0,
                        "episode_offset": int(task["episode_offset"]),
                        "total_transitions": 0,
                        "observed_step_counts": [],
                        "terminal_rewards": [],
                        "exceptions": [
                            {
                                "shard_index": int(task["shard_index"]),
                                "episode_offset": int(task["episode_offset"]),
                                "exception": repr(exc),
                            }
                        ],
                        "elapsed_seconds": 0.0,
                        "output_path": str(task["output_path"]),
                        "sanitized_action_changes": 0,
                        "raw_market_over_cap": 0,
                        "validation": {"status": "FAIL", "checks": {"worker_completed": False}},
                        "episodes": [],
                    }
                )

    shard_summaries.sort(key=lambda item: item["episode_offset"])
    if any(summary["status"] != "PASS" for summary in shard_summaries):
        summary = _parallel_summary(
            status="FAIL",
            episodes=episodes,
            workers=workers,
            started=started,
            output_path=output_path,
            shard_summaries=shard_summaries,
            validation={"status": "SKIPPED"},
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    _merge_npz([Path(summary["output_path"]) for summary in shard_summaries], output_path)
    validation = validate_dataset(output_path)
    summary = _parallel_summary(
        status="PASS" if validation["status"] == "PASS" else "FAIL",
        episodes=episodes,
        workers=workers,
        started=started,
        output_path=output_path,
        shard_summaries=shard_summaries,
        validation=validation,
    )
    _enforce_collection_contract(summary, episodes, expected_transitions)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def benchmark_parallel_collection(
    episodes: int,
    worker_counts: list[int],
    seed_start: int,
    output_dir: Path,
) -> dict[str, Any]:
    """Run small parallel benchmarks and validate each merged dataset."""

    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for workers in worker_counts:
        output_path = output_dir / f"expert_demos_benchmark_{episodes}_w{workers}.npz"
        report_path = output_dir / f"expert_demos_benchmark_{episodes}_w{workers}_report.json"
        summary = collect_expert_demos_parallel(
            episodes=episodes,
            seed_start=seed_start + workers * 10000,
            workers=workers,
            output_path=output_path,
            report_path=report_path,
            expected_transitions=episodes * 719,
        )
        results.append(
            {
                "workers": workers,
                "status": summary["status"],
                "episodes_completed": summary["episodes_completed"],
                "total_transitions": summary["total_transitions"],
                "elapsed_seconds": summary["elapsed_seconds"],
                "games_per_second": summary["episodes_completed"] / max(summary["elapsed_seconds"], 1e-9),
                "transitions_per_second": summary["total_transitions"] / max(summary["elapsed_seconds"], 1e-9),
                "output_path": summary["output_path"],
                "report_path": str(report_path),
            }
        )

    passed = [result for result in results if result["status"] == "PASS"]
    best = max(passed, key=lambda item: item["games_per_second"]) if passed else None
    summary = {
        "status": "PASS" if len(passed) == len(results) else "FAIL",
        "episodes_per_worker_count": episodes,
        "worker_counts": worker_counts,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "best_workers": best["workers"] if best else None,
        "results": results,
    }
    benchmark_report = output_dir / f"parallel_benchmark_{episodes}_games_report.json"
    benchmark_report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def validate_dataset(path: Path) -> dict[str, Any]:
    """Reload and validate a Step 2 NPZ without pickle."""

    with np.load(path, allow_pickle=False) as data:
        features = data["features"]
        opp_features = data["opponent_features"]
        actions_json = data["actions_json"]
        raw_actions_json = data["raw_actions_json"]
        raw_opponent_actions_json = data["raw_opponent_actions_json"] if "raw_opponent_actions_json" in data.files else None
        opponent_actions_json = data["opponent_actions_json"] if "opponent_actions_json" in data.files else None
        rewards = data["rewards"]
        terminals = data["terminals"]
        episode_ids = data["episode_ids"]
        steps = data["steps"]
        opponent_ids = data["opponent_ids"]

        transition_count = int(features.shape[0])
        checks = {
            "features_shape": features.ndim == 2 and features.shape[1] == FEATURE_DIM,
            "features_dtype": features.dtype == np.float32,
            "features_finite": bool(np.isfinite(features).all()),
            "opponent_features_shape": opp_features.shape == (transition_count, 24),
            "opponent_features_dtype": opp_features.dtype == np.float32,
            "opponent_features_match_slice": bool(np.allclose(opp_features, features[:, 60:84])),
            "actions_count": actions_json.shape == (transition_count,),
            "actions_reloadable_json": _actions_reloadable(actions_json),
            "raw_actions_count": raw_actions_json.shape == (transition_count,),
            "raw_actions_reloadable_json": _raw_actions_reloadable(raw_actions_json),
            "opponent_actions_count": opponent_actions_json is None or opponent_actions_json.shape == (transition_count,),
            "opponent_actions_reloadable_json": opponent_actions_json is None
            or _actions_reloadable(opponent_actions_json),
            "raw_opponent_actions_count": raw_opponent_actions_json is None
            or raw_opponent_actions_json.shape == (transition_count,),
            "raw_opponent_actions_reloadable_json": raw_opponent_actions_json is None
            or _raw_actions_reloadable(raw_opponent_actions_json),
            "rewards_shape_dtype": rewards.shape == (transition_count,) and rewards.dtype == np.float32,
            "terminals_shape_dtype": terminals.shape == (transition_count,) and terminals.dtype == np.bool_,
            "episode_ids_shape_dtype": episode_ids.shape == (transition_count,) and episode_ids.dtype == np.int32,
            "steps_shape_dtype": steps.shape == (transition_count,) and steps.dtype == np.int16,
            "opponent_ids_shape": opponent_ids.shape == (transition_count,),
            "terminal_count_matches_episodes": int(terminals.sum()) == len(set(int(x) for x in episode_ids.tolist())),
        }

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "transition_count": transition_count,
        "checks": checks,
    }


def _collect_shard(task: dict[str, Any]) -> dict[str, Any]:
    return collect_expert_demos(
        episodes=int(task["episodes"]),
        seed_start=int(task["seed_start"]),
        output_path=Path(task["output_path"]),
        report_path=Path(task["report_path"]),
        episode_offset=int(task["episode_offset"]),
        include_old_model=bool(task.get("include_old_model", False)),
        include_targeted_archetypes=bool(task.get("include_targeted_archetypes", False)),
        old_model_path=Path(task.get("old_model_path", DEFAULT_OLD_MODEL_PATH)),
    )


def _episode_shards(episodes: int, workers: int) -> list[tuple[int, int]]:
    shard_size = math.ceil(episodes / workers)
    return [(offset, min(shard_size, episodes - offset)) for offset in range(0, episodes, shard_size)]


def _merge_npz(shard_paths: list[Path], output_path: Path) -> None:
    arrays: dict[str, list[np.ndarray]] = {}
    bytes_keys = {
        "raw_actions_json",
        "actions_json",
        "raw_opponent_actions_json",
        "opponent_actions_json",
        "opponent_ids",
    }
    for shard_path in shard_paths:
        with np.load(shard_path, allow_pickle=False) as shard:
            for key in shard.files:
                value = shard[key]
                if key in bytes_keys:
                    value = value.astype(np.bytes_)
                arrays.setdefault(key, []).append(value)
    merged = {key: np.concatenate(values, axis=0) for key, values in arrays.items()}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **merged)


def _parallel_summary(
    status: str,
    episodes: int,
    workers: int,
    started: float,
    output_path: Path,
    shard_summaries: list[dict[str, Any]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    exceptions = []
    for shard in shard_summaries:
        exceptions.extend(shard.get("exceptions", []))
    episode_reports = []
    for shard in shard_summaries:
        episode_reports.extend(shard.get("episodes", []))
    episode_reports.sort(key=lambda item: item["episode"])
    return {
        "status": status,
        "mode": "parallel",
        "workers": workers,
        "episodes_requested": episodes,
        "episodes_completed": sum(int(shard.get("episodes_completed", 0)) for shard in shard_summaries),
        "total_transitions": sum(int(shard.get("total_transitions", 0)) for shard in shard_summaries),
        "observed_step_counts": [step for shard in shard_summaries for step in shard.get("observed_step_counts", [])],
        "terminal_rewards": [reward for shard in shard_summaries for reward in shard.get("terminal_rewards", [])],
        "exceptions": exceptions,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "expert_policy": str(APEX4_PATH),
        "opponent_cycle": _merged_opponent_cycle(shard_summaries),
        "output_path": str(output_path),
        "sanitized_action_changes": sum(int(shard.get("sanitized_action_changes", 0)) for shard in shard_summaries),
        "raw_market_over_cap": sum(int(shard.get("raw_market_over_cap", 0)) for shard in shard_summaries),
        "validation": validation,
        "shards": shard_summaries,
        "episodes": episode_reports,
    }


def _enforce_collection_contract(
    summary: dict[str, Any],
    expected_episodes: int,
    expected_transitions: int | None,
) -> None:
    if summary["episodes_completed"] != expected_episodes:
        summary["status"] = "FAIL"
        summary.setdefault("contract_failures", []).append(
            f"episodes_completed={summary['episodes_completed']} expected={expected_episodes}"
        )
    if expected_transitions is not None and summary["total_transitions"] != expected_transitions:
        summary["status"] = "FAIL"
        summary.setdefault("contract_failures", []).append(
            f"total_transitions={summary['total_transitions']} expected={expected_transitions}"
        )
    if summary.get("exceptions"):
        summary["status"] = "FAIL"
        summary.setdefault("contract_failures", []).append("exceptions present")
    if summary.get("validation", {}).get("status") != "PASS":
        summary["status"] = "FAIL"
        summary.setdefault("contract_failures", []).append("dataset validation failed")


def _opponent_pool(
    include_old_model: bool = False,
    include_targeted_archetypes: bool = False,
    old_model_path: Path = DEFAULT_OLD_MODEL_PATH,
) -> list[tuple[str, AgentFn]]:
    if include_targeted_archetypes:
        pool = [
            ("livestock_heavy_apex4", load_agent(APEX4_PATH)),
            ("crop_heavy_targeted", crop_heavy_agent),
            ("balanced_pass_only", _pass_agent),
            ("aggressive_expand_targeted", aggressive_expand_agent),
            ("market_manipulator_targeted", market_manipulator_agent),
        ]
    else:
        pool = [
            ("apex35_live_submission", load_agent(APEX35_PATH)),
            ("apex4_self_play", load_agent(APEX4_PATH)),
            ("v18_baseline", load_agent(V18_PATH)),
            ("pass_only", _pass_agent),
        ]
    if include_old_model and old_model_path.exists():
        pool.append(("older_apex_model", load_agent(old_model_path)))
    return pool


def _merged_opponent_cycle(shard_summaries: list[dict[str, Any]]) -> list[str]:
    for shard in shard_summaries:
        cycle = shard.get("opponent_cycle")
        if cycle:
            return list(cycle)
    return []


def _pass_agent(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _random_agent(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    # Reserved for later scaling; not used in the default pilot cycle.
    return {"farmer": [random.choice(["PASS", "MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT"])], "hands": [], "market": []}


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def _validate_features(features: np.ndarray) -> None:
    if features.shape != (FEATURE_DIM,):
        raise AssertionError(f"expected feature shape ({FEATURE_DIM},), got {features.shape}")
    if features.dtype != np.float32:
        raise AssertionError(f"expected feature dtype float32, got {features.dtype}")
    if not np.isfinite(features).all():
        raise AssertionError("features contain NaN or Inf")


def _validate_action(action: dict[str, Any]) -> None:
    if set(action) != {"farmer", "hands", "market"}:
        raise AssertionError(f"invalid action keys: {sorted(action)}")
    if not isinstance(action["farmer"], list) or len(action["farmer"]) < 1:
        raise AssertionError(f"invalid farmer action: {action['farmer']}")
    if not isinstance(action["hands"], list):
        raise AssertionError(f"invalid hands action: {action['hands']}")
    if not isinstance(action["market"], list) or len(action["market"]) > 10:
        raise AssertionError(f"invalid market action count: {action['market']}")
    for order in action["market"]:
        if not isinstance(order, list):
            raise AssertionError(f"market order is not a list: {order!r}")


def _actions_reloadable(actions_json: np.ndarray) -> bool:
    try:
        for row in actions_json[: min(len(actions_json), 1000)]:
            _validate_action(json.loads(_row_text(row)))
    except (TypeError, ValueError, AssertionError, json.JSONDecodeError):
        return False
    return True


def _raw_actions_reloadable(actions_json: np.ndarray) -> bool:
    try:
        for row in actions_json[: min(len(actions_json), 1000)]:
            action = json.loads(_row_text(row))
            if not isinstance(action, dict):
                return False
            if not isinstance(action.get("farmer"), list) or not isinstance(action.get("hands"), list):
                return False
            if not isinstance(action.get("market"), list):
                return False
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return True


def _json_roundtrip(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError):
        return value


def _bytes_array(values: list[str]) -> np.ndarray:
    return np.asarray([value.encode("utf-8") for value in values], dtype=np.bytes_)


def _row_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real APEX 4.0 expert demonstrations.")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--expect-transitions", type=int, default=None)
    parser.add_argument("--include-old-model", action="store_true")
    parser.add_argument("--include-targeted-archetypes", action="store_true")
    parser.add_argument("--old-model-path", type=Path, default=DEFAULT_OLD_MODEL_PATH)
    parser.add_argument("--benchmark-workers", type=int, nargs="*", default=None)
    parser.add_argument("--benchmark-output-dir", type=Path, default=BENCHMARK_DIR / "parallel_benchmarks")
    args = parser.parse_args()

    if args.benchmark_workers:
        summary = benchmark_parallel_collection(
            episodes=args.episodes,
            worker_counts=args.benchmark_workers,
            seed_start=args.seed_start,
            output_dir=args.benchmark_output_dir,
        )
        return 0 if summary["status"] == "PASS" else 1

    summary = collect_expert_demos_parallel(
        episodes=args.episodes,
        seed_start=args.seed_start,
        workers=args.workers,
        output_path=args.output,
        report_path=args.report,
        expected_transitions=args.expect_transitions,
        include_old_model=args.include_old_model,
        include_targeted_archetypes=args.include_targeted_archetypes,
        old_model_path=args.old_model_path,
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "episodes"}, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
