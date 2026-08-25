"""Diagnostic profile for the Step 5B agent-driven rollout path.

This deliberately duplicates the rollout orchestration without changing the
trainer or OPT-1 snapshot. It measures where wall time goes before any tuning.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.strategy_selector import StrategySelector
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    DEFAULT_CLASSIFIER,
    STRATEGY_PROFILES,
    _classifier_probs,
    _configured_apex4_agent,
    _load_classifier,
    _opponent_pool,
    _selector_input,
)
from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action

DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step5b" / "ppo_rollout_profile.json"


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def profile_rollout(
    episodes: int = 2,
    seed_start: int = 64000,
    decision_step: int = 120,
    classifier_path: Path = DEFAULT_CLASSIFIER,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    started = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("CUDA is required for the Step 5B rollout profile")

    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = StrategySelector().to(device).eval()
    opponent_pool = _opponent_pool()
    totals = {
        "observation_and_features": 0.0,
        "classifier_inference": 0.0,
        "selector_inference": 0.0,
        "agent_action_selection": 0.0,
        "environment_step": 0.0,
        "post_step_feature_validation": 0.0,
        "other_rollout": 0.0,
    }
    episode_reports: list[dict[str, Any]] = []

    with torch.no_grad():
        for episode in range(episodes):
            episode_started = time.perf_counter()
            opponent_id, opponent_fn = opponent_pool[episode % len(opponent_pool)]
            env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
            env.reset(seed_start + episode)
            default_agent = _configured_apex4_agent({}, module_suffix=700000 + episode)
            selected_agent = None
            decision = None
            done = False
            steps = 0
            reward = 0.0
            counts = {key: 0 for key in totals}
            episode_totals = {key: 0.0 for key in totals}

            while not done:
                section_started = time.perf_counter()
                obs = env.observation(0)
                features = extract_features(obs)
                if features.shape != (128,) or features.dtype != np.float32 or not np.isfinite(features).all():
                    raise AssertionError("invalid pre-step features")
                elapsed_section = time.perf_counter() - section_started
                totals["observation_and_features"] += elapsed_section
                episode_totals["observation_and_features"] += elapsed_section
                counts["observation_and_features"] += 1

                if decision is None and env.step_count >= decision_step:
                    section_started = time.perf_counter()
                    opp_probs = _classifier_probs(classifier, classifier_meta, features, device)
                    _sync(device)
                    elapsed_section = time.perf_counter() - section_started
                    totals["classifier_inference"] += elapsed_section
                    episode_totals["classifier_inference"] += elapsed_section
                    counts["classifier_inference"] += 1

                    section_started = time.perf_counter()
                    selector_input = _selector_input(features, opp_probs, device)
                    distribution, confidence, _ = selector.distribution(selector_input)
                    strategy_idx = distribution.sample()
                    _sync(device)
                    elapsed_section = time.perf_counter() - section_started
                    totals["selector_inference"] += elapsed_section
                    episode_totals["selector_inference"] += elapsed_section
                    counts["selector_inference"] += 1
                    selected_profile = STRATEGY_PROFILES[int(strategy_idx.item())]
                    selected_agent = _configured_apex4_agent(
                        selected_profile["overrides"], module_suffix=710000 + episode
                    )
                    decision = {
                        "step": int(env.step_count),
                        "strategy": selected_profile["name"],
                        "confidence": float(confidence.squeeze().cpu().item()),
                    }

                section_started = time.perf_counter()
                active_agent = selected_agent if selected_agent is not None else default_agent
                action = sanitize_action(call_agent(active_agent, obs, env.configuration))
                elapsed_section = time.perf_counter() - section_started
                totals["agent_action_selection"] += elapsed_section
                episode_totals["agent_action_selection"] += elapsed_section
                counts["agent_action_selection"] += 1

                section_started = time.perf_counter()
                _, reward, done, info = env.step(action)
                _sync(device)
                elapsed_section = time.perf_counter() - section_started
                totals["environment_step"] += elapsed_section
                episode_totals["environment_step"] += elapsed_section
                counts["environment_step"] += 1

                section_started = time.perf_counter()
                next_features = extract_features(env.observation(0))
                if next_features.shape != (128,) or next_features.dtype != np.float32 or not np.isfinite(next_features).all():
                    raise AssertionError("invalid post-step features")
                elapsed_section = time.perf_counter() - section_started
                totals["post_step_feature_validation"] += elapsed_section
                episode_totals["post_step_feature_validation"] += elapsed_section
                counts["post_step_feature_validation"] += 1
                steps = int(info["step"])

            elapsed = time.perf_counter() - episode_started
            residual = max(0.0, elapsed - sum(episode_totals[key] for key in episode_totals if key != "other_rollout"))
            totals["other_rollout"] += residual
            episode_reports.append(
                {
                    "episode": episode,
                    "seed": seed_start + episode,
                    "opponent_id": opponent_id,
                    "steps": steps,
                    "completed": bool(done),
                    "raw_terminal_reward": float(reward),
                    "decision": decision,
                    "episode_seconds": round(elapsed, 6),
                    "actual_cuda_used": env.actual_cuda_used,
                    "tensor_device": str(env.engine.money.device),
                }
            )

    total_seconds = time.perf_counter() - started
    report = {
        "status": "PASS",
        "scope": "diagnostic only; no PPO update, no source optimization",
        "episodes": episodes,
        "decision_step": decision_step,
        "device": {
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_device_name": torch.cuda.get_device_name(0),
            "selected_device": str(device),
        },
        "engine": "immutable OPT-1 CUDA snapshot via CudaPPOEnv",
        "timing_seconds": {key: round(value, 6) for key, value in totals.items()},
        "timing_per_episode_seconds": {
            key: round(value / max(episodes, 1), 6) for key, value in totals.items()
        },
        "counts": counts,
        "total_seconds": round(total_seconds, 6),
        "games_per_second": episodes / max(total_seconds, 1e-9),
        "episode_reports": episode_reports,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--seed-start", type=int, default=64000)
    parser.add_argument("--decision-step", type=int, default=120)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    print(json.dumps(profile_rollout(args.episodes, args.seed_start, args.decision_step, report_path=args.report), indent=2))


if __name__ == "__main__":
    main()
