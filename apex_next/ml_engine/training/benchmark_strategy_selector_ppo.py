"""Step 5B benchmark run for the APEX 4.1 strategy selector PPO trainer."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.strategy_selector import StrategySelector
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    DEFAULT_CLASSIFIER,
    PPO_CONFIG,
    STRATEGY_PROFILES,
    _classifier_probs,
    _configured_apex4_agent,
    _flat_params,
    _load_classifier,
    _opponent_pool,
    _ppo_update,
    _selector_input,
    _verify_checkpoint_reload,
)
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INITIAL_SELECTOR = ML_ENGINE_DIR / "checkpoints" / "strategy_selector" / "strategy_selector_timing_smoke.pt"
DEFAULT_CHECKPOINT = ML_ENGINE_DIR / "checkpoints" / "benchmarks" / "strategy_selector_step5b_benchmark.pt"
DEFAULT_REPORT = ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_selector_step5b_benchmark_report.json"
_APEX4_MODULE_CACHE: dict[str, Any] = {}


def run_step5b_benchmark(
    episodes: int = 250,
    seed_start: int = 34000,
    decision_step: int = 120,
    classifier_path: Path = DEFAULT_CLASSIFIER,
    initial_selector_path: Path = DEFAULT_INITIAL_SELECTOR,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    report_path: Path = DEFAULT_REPORT,
    require_cuda: bool = True,
    progress_every: int = 10,
    batch_size: int = 1,
) -> dict[str, Any]:
    """Collect one fixed-policy rollout batch, run one PPO update, and report timings."""

    if batch_size > 1:
        return run_step5b_batch_benchmark(
            episodes=episodes,
            seed_start=seed_start,
            decision_step=decision_step,
            classifier_path=classifier_path,
            initial_selector_path=initial_selector_path,
            checkpoint_path=checkpoint_path,
            report_path=report_path,
            require_cuda=require_cuda,
            batch_size=batch_size,
        )

    started = time.perf_counter()
    tracemalloc.start()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for Step 5B benchmark but torch.cuda.is_available() is False")

    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = _load_selector(initial_selector_path, device)
    selector.eval()
    optimizer = torch.optim.Adam(selector.parameters(), lr=PPO_CONFIG["lr"])

    device_checks = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "selected_device": str(device),
        "classifier_device": str(next(classifier.parameters()).device),
        "selector_device": str(next(selector.parameters()).device),
    }

    opponent_pool = _opponent_pool()
    rollout_started = time.perf_counter()
    trajectories: list[dict[str, Any]] = []
    episode_reports: list[dict[str, Any]] = []
    invalid_features = 0
    illegal_action_count = 0

    with torch.no_grad():
        for episode in range(episodes):
            episode_seed = seed_start + episode
            opponent_id, opponent_fn = opponent_pool[episode % len(opponent_pool)]
            result = _rollout_episode(
                episode=episode,
                seed=episode_seed,
                decision_step=decision_step,
                opponent_id=opponent_id,
                opponent_fn=opponent_fn,
                classifier=classifier,
                classifier_meta=classifier_meta,
                selector=selector,
                device=device,
            )
            trajectories.append(result["trajectory"])
            episode_reports.append(result["episode_report"])
            invalid_features += int(result["episode_report"]["invalid_feature_count"])
            illegal_action_count += int(result["episode_report"]["illegal_action_count"])
            if progress_every > 0 and len(episode_reports) % progress_every == 0:
                _write_progress(
                    report_path.with_suffix(".progress.json"),
                    completed=len(episode_reports),
                    total=episodes,
                    rollout_started=rollout_started,
                    latest=result["episode_report"],
                )

    rollout_seconds = time.perf_counter() - rollout_started

    update_started = time.perf_counter()
    selector.train()
    old_params = _flat_params(selector)
    update_stats = _ppo_update(selector, optimizer, trajectories, device)
    new_params = _flat_params(selector)
    update_seconds = time.perf_counter() - update_started
    max_parameter_delta = float((new_params - old_params).abs().max().detach().cpu().item())

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": selector.state_dict(),
            "ppo_config": PPO_CONFIG,
            "strategy_profiles": STRATEGY_PROFILES,
            "source_selector_checkpoint": str(initial_selector_path),
            "source_classifier": str(classifier_path),
            "decision_step": decision_step,
            "episodes_completed": len(episode_reports),
            "benchmark_report_path": str(report_path),
        },
        checkpoint_path,
    )
    checkpoint_reload_ok = _verify_checkpoint_reload(checkpoint_path)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rewards = np.asarray([row["normalized_reward"] for row in episode_reports], dtype=np.float32)
    elapsed_seconds = time.perf_counter() - started
    pass_checks = {
        "all_episodes_completed": len(episode_reports) == episodes
        and all(row["completed"] and row["steps"] == 719 for row in episode_reports),
        "no_invalid_features": invalid_features == 0,
        "no_illegal_actions": illegal_action_count == 0,
        "finite_rewards": bool(np.isfinite(rewards).all()),
        "finite_ppo_losses": bool(update_stats["finite_losses"]),
        "parameter_update": max_parameter_delta > 0.0,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "cuda_used": device.type == "cuda",
    }

    report = {
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "step": "STEP 5B - Strategy Selector PPO benchmark",
        "mode": "single fixed-policy batch benchmark",
        "episodes_requested": episodes,
        "episodes_completed": len(episode_reports),
        "decision_step": decision_step,
        "source_classifier": str(classifier_path),
        "source_selector_checkpoint": str(initial_selector_path),
        "checkpoint_path": str(checkpoint_path),
        "device": device_checks,
        "ppo_config": PPO_CONFIG,
        "opponent_sampling": "uniform round-robin benchmark over configured pool",
        "opponent_pool": [name for name, _ in opponent_pool],
        "reward_definition": "terminal (our_MCV - opponent_MCV) / 100000.0",
        "causal_rule": "classifier and selector input use only the current observation at decision_step",
        "pass_checks": pass_checks,
        "timing": {
            "rollout_seconds": round(rollout_seconds, 6),
            "ppo_update_seconds": round(update_seconds, 6),
            "total_seconds": round(elapsed_seconds, 6),
            "games_per_second_rollout": episodes / max(rollout_seconds, 1e-9),
            "games_per_second_total": episodes / max(elapsed_seconds, 1e-9),
            "estimated_10000_seconds_at_total_rate": 10000.0 / max(episodes / max(elapsed_seconds, 1e-9), 1e-9),
        },
        "memory": {
            "tracemalloc_current_mb": current_mem / (1024 * 1024),
            "tracemalloc_peak_mb": peak_mem / (1024 * 1024),
            "cuda_max_memory_allocated_mb": torch.cuda.max_memory_allocated(device) / (1024 * 1024)
            if device.type == "cuda"
            else None,
            "cuda_max_memory_reserved_mb": torch.cuda.max_memory_reserved(device) / (1024 * 1024)
            if device.type == "cuda"
            else None,
        },
        "reward_summary": {
            "mean": float(rewards.mean()) if rewards.size else 0.0,
            "median": float(np.median(rewards)) if rewards.size else 0.0,
            "p05": float(np.quantile(rewards, 0.05)) if rewards.size else 0.0,
            "min": float(rewards.min()) if rewards.size else 0.0,
            "max": float(rewards.max()) if rewards.size else 0.0,
            "win_rate": float((rewards > 0).mean()) if rewards.size else 0.0,
        },
        "strategy_counts": _counts(row["strategy_name"] for row in episode_reports),
        "opponent_counts": _counts(row["opponent_id"] for row in episode_reports),
        "update_stats": update_stats,
        "max_parameter_delta": max_parameter_delta,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "sample_episode_reports": episode_reports[:20],
        "elapsed_seconds": round(elapsed_seconds, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    progress_path = report_path.with_suffix(".progress.json")
    if progress_path.exists():
        progress_path.unlink()
    return report


def run_step5b_batch_benchmark(
    episodes: int = 32,
    seed_start: int = 65000,
    decision_step: int = 120,
    classifier_path: Path = DEFAULT_CLASSIFIER,
    initial_selector_path: Path = DEFAULT_INITIAL_SELECTOR,
    checkpoint_path: Path = ML_ENGINE_DIR / "checkpoints" / "benchmarks" / "strategy_selector_step5b_batch32.pt",
    report_path: Path = ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_selector_step5b_batch32_report.json",
    require_cuda: bool = True,
    batch_size: int = 32,
    progress_every: int = 10,
) -> dict[str, Any]:
    """Run one fixed-policy PPO update with all episodes in one CUDA batch."""

    if episodes != batch_size:
        raise ValueError("The initial batch pilot requires episodes == batch_size")
    started = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for the batch PPO benchmark")
    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = _load_selector(initial_selector_path, device).eval()
    optimizer = torch.optim.Adam(selector.parameters(), lr=PPO_CONFIG["lr"])
    opponent_pool = _opponent_pool()
    opponent_ids = [opponent_pool[idx % len(opponent_pool)][0] for idx in range(batch_size)]
    opponent_fns = [_opponent_pool()[idx % len(opponent_pool)][1] for idx in range(batch_size)]
    env = CudaBatchPPOEnv(opponent_fns, device="cuda:0")
    seeds = [seed_start + idx for idx in range(batch_size)]
    env.reset(seeds, extract_initial_features=False)
    default_agents = [_configured_apex4_agent({}, module_suffix=800000 + idx) for idx in range(batch_size)]
    selected_agents: list[Any] = [None] * batch_size
    decision_records: list[dict[str, Any] | None] = [None] * batch_size
    invalid_features = 0
    illegal_actions = 0
    steps = 0
    feature_extractions = 0
    decision_feature_hash = hashlib.sha256()
    rollout_started = time.perf_counter()

    with torch.no_grad():
        done = [False] * batch_size
        while not all(done):
            observations = [env.observation(idx, 0) for idx in range(batch_size)]
            decision_due = env.step_count >= decision_step and all(record is None for record in decision_records)
            feature_batch = [extract_features(obs) for obs in observations] if decision_due else []
            if decision_due:
                feature_extractions += batch_size
                invalid_features += sum(
                    int(features.shape != (128,) or features.dtype != np.float32 or not np.isfinite(features).all())
                    for features in feature_batch
                )
                for idx, features in enumerate(feature_batch):
                    decision_feature_hash.update(features.tobytes())
                    opp_probs = _classifier_probs(classifier, classifier_meta, features, device)
                    selector_input = _selector_input(features, opp_probs, device)
                    distribution, confidence, _ = selector.distribution(selector_input)
                    strategy_idx = distribution.sample()
                    selected_profile = STRATEGY_PROFILES[int(strategy_idx.item())]
                    selected_agents[idx] = _configured_apex4_agent(
                        selected_profile["overrides"], module_suffix=810000 + idx
                    )
                    decision_records[idx] = {
                        "state": selector_input.detach().squeeze(0),
                        "action": strategy_idx.detach().squeeze(0),
                        "old_log_prob": distribution.log_prob(strategy_idx).detach().squeeze(0),
                        "old_strategy_probs": distribution.probs.detach().squeeze(0),
                        "strategy_index": int(strategy_idx.item()),
                        "strategy_name": selected_profile["name"],
                        "strategy_weight_sum": float(distribution.probs[0].sum().detach().cpu().item()),
                        "confidence": float(confidence.squeeze().detach().cpu().item()),
                        "decision_uses_observation_step": int(env.step_count),
                        "classifier_probs": [float(item) for item in opp_probs],
                    }
            actions = []
            for idx, obs in enumerate(observations):
                active_agent = selected_agents[idx] if selected_agents[idx] is not None else default_agents[idx]
                action = sanitize_action(call_agent(active_agent, obs, env.configuration))
                if not _valid_action_shell(action):
                    illegal_actions += 1
                actions.append(action)
            _, rewards, done, infos = env.step(actions, extract_next_features=False)
            steps = int(infos[0]["step"])
            if steps > 720:
                raise AssertionError(f"batch PPO episode exceeded 720 steps: {steps}")
    rollout_seconds = time.perf_counter() - rollout_started

    trajectories = []
    episode_reports = []
    for idx, record in enumerate(decision_records):
        if record is None:
            raise AssertionError(f"decision step {decision_step} was never reached for batch item {idx}")
        normalized_reward = float(env.engine.terminal_metrics(idx, 0)["normalized_reward"])
        trajectories.append(
            {
                "state": record["state"],
                "action": record["action"],
                "old_log_prob": record["old_log_prob"],
                "old_strategy_probs": record["old_strategy_probs"],
                "reward": normalized_reward,
            }
        )
        episode_reports.append(
            {
                "episode": idx,
                "seed": seeds[idx],
                "opponent_id": opponent_ids[idx],
                "completed": bool(done[idx]),
                "steps": steps,
                "raw_terminal_reward": float(env.engine.terminal_metrics(idx, 0)["raw_terminal_reward"]),
                "normalized_reward": normalized_reward,
                "invalid_feature_count": 0,
                "illegal_action_count": 0,
                **{
                    key: value
                    for key, value in record.items()
                    if key not in {"state", "action", "old_log_prob", "old_strategy_probs"}
                },
            }
        )

    update_started = time.perf_counter()
    selector.train()
    old_params = _flat_params(selector)
    update_stats = _ppo_update(selector, optimizer, trajectories, device)
    new_params = _flat_params(selector)
    update_seconds = time.perf_counter() - update_started
    max_parameter_delta = float((new_params - old_params).abs().max().detach().cpu().item())
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": selector.state_dict(),
            "ppo_config": PPO_CONFIG,
            "strategy_profiles": STRATEGY_PROFILES,
            "source_selector_checkpoint": str(initial_selector_path),
            "source_classifier": str(classifier_path),
            "decision_step": decision_step,
            "batch_size": batch_size,
            "benchmark_report_path": str(report_path),
        },
        checkpoint_path,
    )
    checkpoint_reload_ok = _verify_checkpoint_reload(checkpoint_path)
    rewards = np.asarray([row["normalized_reward"] for row in episode_reports], dtype=np.float32)
    elapsed_seconds = time.perf_counter() - started
    pass_checks = {
        "all_episodes_completed": len(episode_reports) == episodes and all(row["completed"] and row["steps"] == 719 for row in episode_reports),
        "no_invalid_features": invalid_features == 0,
        "no_illegal_actions": illegal_actions == 0,
        "finite_rewards": bool(np.isfinite(rewards).all()),
        "finite_ppo_losses": bool(update_stats["finite_losses"]),
        "parameter_update": max_parameter_delta > 0.0,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "cuda_used": bool(env.actual_cuda_used),
        "decision_step_correct": all(row["decision_uses_observation_step"] == decision_step for row in episode_reports),
    }
    report = {
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "step": "STEP 5B OPT-6 batch PPO pilot",
        "mode": "single fixed-policy CUDA batch",
        "episodes_requested": episodes,
        "episodes_completed": len(episode_reports),
        "batch_size": batch_size,
        "decision_step": decision_step,
        "engine": "immutable OPT-1 CUDA snapshot",
        "optimization": "OPT-7 skip non-decision feature extraction",
        "feature_extractions": feature_extractions,
        "decision_feature_sha256": decision_feature_hash.hexdigest(),
        "device": {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "selected_device": str(device),
            "engine_tensor_device": str(env.engine.money.device),
        },
        "pass_checks": pass_checks,
        "timing": {
            "rollout_seconds": rollout_seconds,
            "ppo_update_seconds": update_seconds,
            "total_seconds": elapsed_seconds,
            "games_per_second_rollout": episodes / max(rollout_seconds, 1e-9),
            "games_per_second_total": episodes / max(elapsed_seconds, 1e-9),
        },
        "reward_summary": {
            "mean": float(rewards.mean()),
            "p05": float(np.quantile(rewards, 0.05)),
            "win_rate": float((rewards > 0).mean()),
        },
        "update_stats": update_stats,
        "max_parameter_delta": max_parameter_delta,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "episode_reports": episode_reports,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_step5b_parallel_benchmark(
    episodes: int = 250,
    seed_start: int = 34000,
    workers: int = 2,
    decision_step: int = 120,
    classifier_path: Path = DEFAULT_CLASSIFIER,
    initial_selector_path: Path = DEFAULT_INITIAL_SELECTOR,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    report_path: Path = DEFAULT_REPORT,
    require_cuda: bool = True,
    progress_every: int = 1,
) -> dict[str, Any]:
    """Collect fixed-policy rollouts in isolated workers, then update once on CUDA."""

    started = time.perf_counter()
    tracemalloc.start()
    workers = max(1, int(workers))
    if workers == 1:
        return run_step5b_benchmark(
            episodes=episodes,
            seed_start=seed_start,
            decision_step=decision_step,
            classifier_path=classifier_path,
            initial_selector_path=initial_selector_path,
            checkpoint_path=checkpoint_path,
            report_path=report_path,
            require_cuda=require_cuda,
            progress_every=max(1, progress_every * 10),
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for Step 5B benchmark but torch.cuda.is_available() is False")

    classifier, _ = _load_classifier(classifier_path, device)
    selector = _load_selector(initial_selector_path, device)
    optimizer = torch.optim.Adam(selector.parameters(), lr=PPO_CONFIG["lr"])
    device_checks = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "selected_device": str(device),
        "classifier_device": str(next(classifier.parameters()).device),
        "selector_device": str(next(selector.parameters()).device),
        "worker_inference_device": "cpu",
    }

    rollout_started = time.perf_counter()
    tasks = []
    for shard_index, (offset, count) in enumerate(_episode_shards(episodes, workers)):
        if count <= 0:
            continue
        tasks.append(
            {
                "shard_index": shard_index,
                "episodes": count,
                "seed_start": seed_start,
                "episode_offset": offset,
                "decision_step": decision_step,
                "classifier_path": classifier_path,
                "initial_selector_path": initial_selector_path,
            }
        )

    shard_results = []
    completed = 0
    context = mp.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        future_to_task = {executor.submit(_rollout_shard, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - report exact worker failure.
                result = {
                    "status": "FAIL",
                    "shard_index": int(task["shard_index"]),
                    "episode_offset": int(task["episode_offset"]),
                    "episodes_completed": 0,
                    "trajectories": [],
                    "episode_reports": [],
                    "exceptions": [repr(exc)],
                    "elapsed_seconds": 0.0,
                }
            shard_results.append(result)
            completed += int(result.get("episodes_completed", 0))
            if progress_every > 0:
                _write_progress(
                    report_path.with_suffix(".progress.json"),
                    completed=completed,
                    total=episodes,
                    rollout_started=rollout_started,
                    latest={
                        "shard_index": result.get("shard_index"),
                        "status": result.get("status"),
                        "episodes_completed": result.get("episodes_completed", 0),
                    },
                )

    rollout_seconds = time.perf_counter() - rollout_started
    shard_results.sort(key=lambda item: item["episode_offset"])
    worker_failed = any(result["status"] != "PASS" for result in shard_results)
    episode_reports = [row for result in shard_results for row in result["episode_reports"]]
    episode_reports.sort(key=lambda item: item["episode"])
    trajectories = [_trajectory_from_wire(row, device) for result in shard_results for row in result["trajectories"]]

    update_started = time.perf_counter()
    selector.train()
    old_params = _flat_params(selector)
    update_stats = _ppo_update(selector, optimizer, trajectories, device) if trajectories else {"finite_losses": False}
    new_params = _flat_params(selector)
    update_seconds = time.perf_counter() - update_started
    max_parameter_delta = float((new_params - old_params).abs().max().detach().cpu().item())

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": selector.state_dict(),
            "ppo_config": PPO_CONFIG,
            "strategy_profiles": STRATEGY_PROFILES,
            "source_selector_checkpoint": str(initial_selector_path),
            "source_classifier": str(classifier_path),
            "decision_step": decision_step,
            "episodes_completed": len(episode_reports),
            "workers": workers,
            "benchmark_report_path": str(report_path),
        },
        checkpoint_path,
    )
    checkpoint_reload_ok = _verify_checkpoint_reload(checkpoint_path)
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rewards = np.asarray([row["normalized_reward"] for row in episode_reports], dtype=np.float32)
    invalid_features = sum(int(row["invalid_feature_count"]) for row in episode_reports)
    illegal_action_count = sum(int(row["illegal_action_count"]) for row in episode_reports)
    elapsed_seconds = time.perf_counter() - started
    pass_checks = {
        "all_episodes_completed": len(episode_reports) == episodes
        and all(row["completed"] and row["steps"] == 719 for row in episode_reports),
        "workers_completed": not worker_failed,
        "no_invalid_features": invalid_features == 0,
        "no_illegal_actions": illegal_action_count == 0,
        "finite_rewards": bool(rewards.size and np.isfinite(rewards).all()),
        "finite_ppo_losses": bool(update_stats["finite_losses"]),
        "parameter_update": max_parameter_delta > 0.0,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "cuda_used": device.type == "cuda",
    }
    report = {
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "step": "STEP 5B - Strategy Selector PPO parallel benchmark",
        "mode": "parallel fixed-policy batch benchmark",
        "episodes_requested": episodes,
        "episodes_completed": len(episode_reports),
        "workers": workers,
        "decision_step": decision_step,
        "source_classifier": str(classifier_path),
        "source_selector_checkpoint": str(initial_selector_path),
        "checkpoint_path": str(checkpoint_path),
        "device": device_checks,
        "ppo_config": PPO_CONFIG,
        "opponent_sampling": "uniform round-robin benchmark over configured pool",
        "opponent_pool": [name for name, _ in _opponent_pool()],
        "reward_definition": "terminal (our_MCV - opponent_MCV) / 100000.0",
        "causal_rule": "worker classifier and selector input use only the current observation at decision_step",
        "policy_snapshot_rule": "workers collect with the initial selector checkpoint; PPO update starts only after all workers finish",
        "pass_checks": pass_checks,
        "timing": {
            "rollout_seconds": round(rollout_seconds, 6),
            "ppo_update_seconds": round(update_seconds, 6),
            "total_seconds": round(elapsed_seconds, 6),
            "games_per_second_rollout": episodes / max(rollout_seconds, 1e-9),
            "games_per_second_total": episodes / max(elapsed_seconds, 1e-9),
            "estimated_10000_seconds_at_total_rate": 10000.0 / max(episodes / max(elapsed_seconds, 1e-9), 1e-9),
        },
        "memory": {
            "tracemalloc_current_mb": current_mem / (1024 * 1024),
            "tracemalloc_peak_mb": peak_mem / (1024 * 1024),
            "cuda_max_memory_allocated_mb": torch.cuda.max_memory_allocated(device) / (1024 * 1024)
            if device.type == "cuda"
            else None,
            "cuda_max_memory_reserved_mb": torch.cuda.max_memory_reserved(device) / (1024 * 1024)
            if device.type == "cuda"
            else None,
            "worker_peak_tracemalloc_mb": max(
                (float(result.get("tracemalloc_peak_mb", 0.0)) for result in shard_results), default=0.0
            ),
        },
        "reward_summary": {
            "mean": float(rewards.mean()) if rewards.size else 0.0,
            "median": float(np.median(rewards)) if rewards.size else 0.0,
            "p05": float(np.quantile(rewards, 0.05)) if rewards.size else 0.0,
            "min": float(rewards.min()) if rewards.size else 0.0,
            "max": float(rewards.max()) if rewards.size else 0.0,
            "win_rate": float((rewards > 0).mean()) if rewards.size else 0.0,
        },
        "strategy_counts": _counts(row["strategy_name"] for row in episode_reports),
        "opponent_counts": _counts(row["opponent_id"] for row in episode_reports),
        "update_stats": update_stats,
        "max_parameter_delta": max_parameter_delta,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "shards": [
            {key: value for key, value in result.items() if key not in {"trajectories", "episode_reports"}}
            for result in shard_results
        ],
        "sample_episode_reports": episode_reports[:20],
        "elapsed_seconds": round(elapsed_seconds, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    progress_path = report_path.with_suffix(".progress.json")
    if progress_path.exists():
        progress_path.unlink()
    return report


def _rollout_episode(
    episode: int,
    seed: int,
    decision_step: int,
    opponent_id: str,
    opponent_fn: Any,
    classifier: Any,
    classifier_meta: dict[str, Any],
    selector: StrategySelector,
    device: torch.device,
) -> dict[str, Any]:
    env = CudaPPOEnv(opponent_fn=opponent_fn, device=str(device))
    env.reset(seed=seed)
    default_agent = _configured_apex4_agent_cached("default", {})
    selected_agent = None
    decision_record: dict[str, Any] | None = None
    trajectory: dict[str, Any] | None = None
    done = False
    reward = 0.0
    steps = 0
    invalid_features = 0
    illegal_action_count = 0

    while not done:
        obs = env.observation(0)
        features = extract_features(obs)
        if features.shape != (128,) or features.dtype != np.float32 or not np.isfinite(features).all():
            invalid_features += 1

        if decision_record is None and env.step_count >= decision_step:
            opp_probs = _classifier_probs(classifier, classifier_meta, features, device)
            selector_input = _selector_input(features, opp_probs, device)
            distribution, confidence, value = selector.distribution(selector_input)
            strategy_idx = distribution.sample()
            selected_profile = STRATEGY_PROFILES[int(strategy_idx.item())]
            selected_agent = _configured_apex4_agent_cached(selected_profile["name"], selected_profile["overrides"])
            strategy_weights = distribution.probs.detach().cpu().numpy()[0]
            decision_record = {
                "decision_uses_observation_step": int(env.step_count),
                "strategy_index": int(strategy_idx.item()),
                "strategy_name": selected_profile["name"],
                "strategy_weight_sum": float(strategy_weights.sum()),
                "confidence": float(confidence.detach().cpu().item()),
                "classifier_probs": [float(item) for item in opp_probs],
            }
            trajectory = {
                "state": selector_input.detach().squeeze(0),
                "action": strategy_idx.detach().squeeze(0),
                "old_log_prob": distribution.log_prob(strategy_idx).detach().squeeze(0),
                "old_strategy_probs": distribution.probs.detach().squeeze(0),
                "reward": 0.0,
            }

        active_agent = selected_agent if selected_agent is not None else default_agent
        raw_action = call_agent(active_agent, obs, env.configuration)
        action = sanitize_action(raw_action)
        if not _valid_action_shell(action):
            illegal_action_count += 1
        next_features, reward, done, info = env.step(action)
        if next_features.shape != (128,) or next_features.dtype != np.float32 or not np.isfinite(next_features).all():
            invalid_features += 1
        steps = int(info["step"])
        if steps > 720:
            raise AssertionError(f"Step 5B benchmark episode exceeded 720 steps: {steps}")

    if decision_record is None or trajectory is None:
        raise AssertionError(f"decision step {decision_step} was never reached")
    normalized_reward = float(reward) / 100000.0
    trajectory["reward"] = normalized_reward
    return {
        "trajectory": trajectory,
        "episode_report": {
            "episode": episode,
            "seed": seed,
            "opponent_id": opponent_id,
            "completed": bool(done),
            "steps": steps,
            "raw_terminal_reward": float(reward),
            "normalized_reward": normalized_reward,
            "invalid_feature_count": invalid_features,
            "illegal_action_count": illegal_action_count,
            **decision_record,
        },
    }


def _rollout_shard(task: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    tracemalloc.start()
    cpu = torch.device("cpu")
    classifier, classifier_meta = _load_classifier(Path(task["classifier_path"]), cpu)
    selector = _load_selector(Path(task["initial_selector_path"]), cpu)
    selector.eval()
    opponent_pool = _opponent_pool()
    trajectories = []
    episode_reports = []
    exceptions = []
    for local_episode in range(int(task["episodes"])):
        episode = int(task["episode_offset"]) + local_episode
        seed = int(task["seed_start"]) + episode
        opponent_id, opponent_fn = opponent_pool[episode % len(opponent_pool)]
        try:
            result = _rollout_episode(
                episode=episode,
                seed=seed,
                decision_step=int(task["decision_step"]),
                opponent_id=opponent_id,
                opponent_fn=opponent_fn,
                classifier=classifier,
                classifier_meta=classifier_meta,
                selector=selector,
                device=cpu,
            )
            trajectories.append(_trajectory_to_wire(result["trajectory"]))
            episode_reports.append(result["episode_report"])
        except Exception as exc:  # noqa: BLE001 - keep shard report exact.
            exceptions.append({"episode": episode, "seed": seed, "exception": repr(exc)})
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    status = "PASS" if not exceptions and len(episode_reports) == int(task["episodes"]) else "FAIL"
    return {
        "status": status,
        "shard_index": int(task["shard_index"]),
        "episode_offset": int(task["episode_offset"]),
        "episodes_requested": int(task["episodes"]),
        "episodes_completed": len(episode_reports),
        "trajectories": trajectories,
        "episode_reports": episode_reports,
        "exceptions": exceptions,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "tracemalloc_peak_mb": peak_mem / (1024 * 1024),
    }


def _trajectory_to_wire(trajectory: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": trajectory["state"].detach().cpu().numpy().astype(np.float32),
        "action": int(trajectory["action"].detach().cpu().item()),
        "old_log_prob": float(trajectory["old_log_prob"].detach().cpu().item()),
        "reward": float(trajectory["reward"]),
    }


def _trajectory_from_wire(trajectory: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        "state": torch.as_tensor(trajectory["state"], dtype=torch.float32, device=device),
        "action": torch.tensor(trajectory["action"], dtype=torch.long, device=device),
        "old_log_prob": torch.tensor(trajectory["old_log_prob"], dtype=torch.float32, device=device),
        "reward": float(trajectory["reward"]),
    }


def _episode_shards(episodes: int, workers: int) -> list[tuple[int, int]]:
    shard_size = math.ceil(episodes / workers)
    shards = []
    for worker_index in range(workers):
        offset = worker_index * shard_size
        count = min(shard_size, episodes - offset)
        if count > 0:
            shards.append((offset, count))
    return shards


def _load_selector(path: Path, device: torch.device) -> StrategySelector:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    selector = StrategySelector().to(device)
    selector.load_state_dict(checkpoint["model_state_dict"])
    return selector


def _configured_apex4_agent_cached(cache_key: str, overrides: dict[str, Any]) -> Any:
    module = _APEX4_MODULE_CACHE.get(cache_key)
    if module is None:
        module_name = f"apex4_step5b_benchmark_{cache_key.lower()}_{time.time_ns()}"
        spec = importlib.util.spec_from_file_location(module_name, PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py")
        if spec is None or spec.loader is None:
            raise ImportError("Could not load APEX4_SUBMISSION_FINAL.py for Step 5B benchmark")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _APEX4_MODULE_CACHE[cache_key] = module
    module.configure_strategy(overrides)
    return module.agent


def _valid_action_shell(action: Any) -> bool:
    return (
        isinstance(action, dict)
        and isinstance(action.get("farmer"), list)
        and isinstance(action.get("hands"), list)
        and isinstance(action.get("market"), list)
        and len(action.get("market", [])) <= 10
    )


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _write_progress(path: Path, completed: int, total: int, rollout_started: float, latest: dict[str, Any]) -> None:
    elapsed = time.perf_counter() - rollout_started
    games_per_second = completed / max(elapsed, 1e-9)
    remaining = max(0, total - completed)
    eta_seconds = remaining / max(games_per_second, 1e-9)
    progress = {
        "completed": completed,
        "total": total,
        "elapsed_seconds": round(elapsed, 3),
        "games_per_second": games_per_second,
        "eta_seconds": eta_seconds,
        "latest_episode": latest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    print(
        f"[step5b-benchmark] {completed}/{total} games "
        f"elapsed={elapsed:.1f}s rate={games_per_second:.4f} games/s eta={eta_seconds / 60.0:.1f}m",
        flush=True,
    )


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Step 5B PPO benchmark batch.")
    parser.add_argument("--episodes", type=int, default=250)
    parser.add_argument("--seed-start", type=int, default=34000)
    parser.add_argument("--decision-step", type=int, default=120)
    parser.add_argument("--classifier", type=Path, default=DEFAULT_CLASSIFIER)
    parser.add_argument("--initial-selector", type=Path, default=DEFAULT_INITIAL_SELECTOR)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    runner = run_step5b_parallel_benchmark if args.workers > 1 else run_step5b_benchmark
    report = runner(
        episodes=args.episodes,
        seed_start=args.seed_start,
        decision_step=args.decision_step,
        classifier_path=args.classifier,
        initial_selector_path=args.initial_selector,
        checkpoint_path=args.checkpoint,
        report_path=args.report,
        require_cuda=not args.allow_cpu,
        progress_every=args.progress_every,
        batch_size=args.batch_size,
        **({"workers": args.workers} if args.workers > 1 else {}),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
