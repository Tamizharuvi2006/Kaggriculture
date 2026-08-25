"""Step 5A diagnostic for choosing a causal strategy-selection time."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import KaggricultureGymEnv, call_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.strategy_selector import StrategySelector
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    DEFAULT_CLASSIFIER,
    DEFAULT_CHECKPOINT as DEFAULT_SELECTOR_CHECKPOINT,
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


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_timing_diagnostic_report.json"
DEFAULT_OUTPUT_CHECKPOINT = ML_ENGINE_DIR / "checkpoints" / "strategy_selector" / "strategy_selector_timing_smoke.pt"


def run_strategy_timing_diagnostic(
    decision_steps: tuple[int, ...] = (0, 120, 240),
    seed_start: int = 33000,
    classifier_path: Path = DEFAULT_CLASSIFIER,
    selector_checkpoint_path: Path = DEFAULT_SELECTOR_CHECKPOINT,
    output_checkpoint_path: Path = DEFAULT_OUTPUT_CHECKPOINT,
    report_path: Path = DEFAULT_REPORT,
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Compare candidate decision points using only observations available by that step."""

    started = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for Step 5A timing diagnostic but torch.cuda.is_available() is False")

    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = _load_selector(selector_checkpoint_path, device)
    selector.eval()

    device_checks = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "selected_device": str(device),
        "classifier_device": str(next(classifier.parameters()).device),
        "selector_device": str(next(selector.parameters()).device),
    }

    opponent_pool = _opponent_pool()
    episode_reports: list[dict[str, Any]] = []
    ppo_trajectories: list[dict[str, Any]] = []
    invalid_features = 0
    future_leakage_checks = []

    for decision_step in decision_steps:
        for opponent_index, (opponent_id, opponent_fn) in enumerate(opponent_pool):
            episode_seed = seed_start + decision_step * 100 + opponent_index
            result = _run_timing_episode(
                decision_step=decision_step,
                seed=episode_seed,
                opponent_id=opponent_id,
                opponent_fn=opponent_fn,
                classifier=classifier,
                classifier_meta=classifier_meta,
                selector=selector,
                device=device,
                module_suffix=decision_step * 100 + opponent_index,
            )
            episode_reports.append(result["episode_report"])
            ppo_trajectories.append(result["trajectory"])
            invalid_features += int(result["episode_report"]["invalid_feature_count"])
            future_leakage_checks.append(result["episode_report"]["decision_uses_observation_step"] <= decision_step)

    update_selector = _load_selector(selector_checkpoint_path, device)
    optimizer = torch.optim.Adam(update_selector.parameters(), lr=PPO_CONFIG["lr"])
    old_params = _flat_params(update_selector)
    update_stats = _ppo_update(update_selector, optimizer, ppo_trajectories, device)
    new_params = _flat_params(update_selector)
    max_parameter_delta = float((new_params - old_params).abs().max().detach().cpu().item())

    output_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": update_selector.state_dict(),
            "ppo_config": PPO_CONFIG,
            "strategy_profiles": STRATEGY_PROFILES,
            "source_selector_checkpoint": str(selector_checkpoint_path),
            "source_classifier": str(classifier_path),
            "diagnostic_report_path": str(report_path),
        },
        output_checkpoint_path,
    )
    checkpoint_reload_ok = _verify_checkpoint_reload(output_checkpoint_path)

    summary_by_step = _summarize_by_decision_step(episode_reports)
    recommended_step = _recommend_decision_step(summary_by_step)
    pass_checks = {
        "all_episodes_completed": all(report["completed"] and report["steps"] == 719 for report in episode_reports),
        "no_invalid_features": invalid_features == 0,
        "finite_classifier_probs": all(report["classifier_probs_finite"] for report in episode_reports),
        "finite_selector_outputs": all(report["selector_outputs_finite"] for report in episode_reports),
        "valid_strategy_weights": all(abs(report["strategy_weight_sum"] - 1.0) <= 1e-5 for report in episode_reports),
        "confidence_in_range": all(0.0 <= report["confidence"] <= 1.0 for report in episode_reports),
        "no_future_leakage": all(future_leakage_checks),
        "classifier_changes_after_opening": any(
            step != 0 and values["mean_classifier_l1_delta_from_t0"] > 0.05
            for step, values in summary_by_step.items()
        ),
        "strategy_changes_after_opening": any(
            step != 0 and values["mean_strategy_l1_delta_from_t0"] > 0.001
            for step, values in summary_by_step.items()
        ),
        "ppo_losses_finite": bool(update_stats["finite_losses"]),
        "ppo_parameter_update": max_parameter_delta > 0.0,
        "checkpoint_reload_ok": checkpoint_reload_ok,
    }

    report = {
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "step": "STEP 5A - Strategy Selection Timing Diagnostic",
        "mode": "small causal timing comparison",
        "decision_steps": list(decision_steps),
        "source_classifier": str(classifier_path),
        "source_selector_checkpoint": str(selector_checkpoint_path),
        "output_checkpoint_path": str(output_checkpoint_path),
        "device": device_checks,
        "opponent_pool": [name for name, _ in opponent_pool],
        "games_run": len(episode_reports),
        "reward_definition": "terminal (our_MCV - opponent_MCV) / 100000.0",
        "causal_rule": "decision features are extracted from current observation before applying the selected strategy; no terminal/future state is used for classifier or selector input",
        "pass_checks": pass_checks,
        "summary_by_decision_step": summary_by_step,
        "recommended_decision_step": recommended_step,
        "update_stats": update_stats,
        "max_parameter_delta": max_parameter_delta,
        "checkpoint_reload_ok": checkpoint_reload_ok,
        "episode_reports": episode_reports,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _run_timing_episode(
    decision_step: int,
    seed: int,
    opponent_id: str,
    opponent_fn: Any,
    classifier: Any,
    classifier_meta: dict[str, Any],
    selector: StrategySelector,
    device: torch.device,
    module_suffix: int,
) -> dict[str, Any]:
    env = KaggricultureGymEnv(opponent_fn=opponent_fn)
    initial_features = env.reset(seed=seed)
    t0_probs = _classifier_probs(classifier, classifier_meta, initial_features, device)
    t0_selector_input = _selector_input(initial_features, t0_probs, device)
    with torch.no_grad():
        t0_dist, t0_confidence, _ = selector.distribution(t0_selector_input)
    t0_weights = t0_dist.probs.detach().cpu().numpy()[0]

    default_agent = _configured_apex4_agent({}, module_suffix=module_suffix * 10)
    selected_agent = None
    decision_record: dict[str, Any] | None = None
    trajectory: dict[str, Any] | None = None
    reward = 0.0
    done = False
    invalid_features = 0
    steps = 0

    while not done:
        if env.state is None:
            raise AssertionError("environment state unexpectedly missing during Step 5A diagnostic")
        obs = _observation(env.state[0])
        features = extract_features(obs)
        if features.shape != (128,) or features.dtype != np.float32 or not np.isfinite(features).all():
            invalid_features += 1

        if decision_record is None and env.step_count >= decision_step:
            decision_features = features
            decision_probs = _classifier_probs(classifier, classifier_meta, decision_features, device)
            selector_input = _selector_input(decision_features, decision_probs, device)
            distribution, confidence, value = selector.distribution(selector_input)
            strategy_idx = distribution.sample()
            selected_profile = STRATEGY_PROFILES[int(strategy_idx.item())]
            selected_agent = _configured_apex4_agent(selected_profile["overrides"], module_suffix=module_suffix * 10 + 1)
            strategy_weights = distribution.probs.detach().cpu().numpy()[0]
            decision_record = {
                "decision_step": decision_step,
                "decision_uses_observation_step": int(env.step_count),
                "strategy_index": int(strategy_idx.item()),
                "strategy_name": selected_profile["name"],
                "strategy_weights": [float(item) for item in strategy_weights],
                "strategy_weight_sum": float(strategy_weights.sum()),
                "confidence": float(confidence.detach().cpu().item()),
                "classifier_probs": [float(item) for item in decision_probs],
                "classifier_probs_finite": bool(np.isfinite(decision_probs).all()),
                "selector_outputs_finite": bool(np.isfinite(strategy_weights).all() and np.isfinite(float(confidence.detach().cpu().item()))),
                "classifier_l1_delta_from_t0": float(np.abs(decision_probs - t0_probs).sum()),
                "strategy_l1_delta_from_t0": float(np.abs(strategy_weights - t0_weights).sum()),
                "t0_classifier_probs": [float(item) for item in t0_probs],
                "t0_strategy_weights": [float(item) for item in t0_weights],
                "t0_confidence": float(t0_confidence.detach().cpu().item()),
            }
            trajectory = {
                "state": selector_input.detach().squeeze(0),
                "action": strategy_idx.detach().squeeze(0),
                "old_log_prob": distribution.log_prob(strategy_idx).detach().squeeze(0),
                "reward": 0.0,
            }

        active_agent = selected_agent if selected_agent is not None else default_agent
        action = sanitize_action(call_agent(active_agent, obs, env.env.configuration))
        next_features, reward, done, info = env.step(action)
        if next_features.shape != (128,) or next_features.dtype != np.float32 or not np.isfinite(next_features).all():
            invalid_features += 1
        steps = int(info["step"])
        if steps > 720:
            raise AssertionError(f"Step 5A diagnostic episode exceeded 720 steps: {steps}")

    if decision_record is None or trajectory is None:
        raise AssertionError(f"decision step {decision_step} was never reached")
    normalized_reward = float(reward) / 100000.0
    trajectory["reward"] = normalized_reward
    episode_report = {
        "seed": seed,
        "opponent_id": opponent_id,
        "completed": bool(done),
        "steps": steps,
        "invalid_feature_count": invalid_features,
        "raw_terminal_reward": float(reward),
        "normalized_reward": normalized_reward,
        **decision_record,
    }
    return {"episode_report": episode_report, "trajectory": trajectory}


def _summarize_by_decision_step(episode_reports: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    summary: dict[int, dict[str, Any]] = {}
    for step in sorted({int(report["decision_step"]) for report in episode_reports}):
        rows = [report for report in episode_reports if int(report["decision_step"]) == step]
        rewards = np.asarray([row["normalized_reward"] for row in rows], dtype=np.float32)
        classifier_deltas = np.asarray([row["classifier_l1_delta_from_t0"] for row in rows], dtype=np.float32)
        strategy_deltas = np.asarray([row["strategy_l1_delta_from_t0"] for row in rows], dtype=np.float32)
        confidence = np.asarray([row["confidence"] for row in rows], dtype=np.float32)
        strategies = sorted({row["strategy_name"] for row in rows})
        summary[step] = {
            "games": len(rows),
            "mean_reward": float(rewards.mean()),
            "win_rate": float((rewards > 0).mean()),
            "min_reward": float(rewards.min()),
            "p05_reward": float(np.quantile(rewards, 0.05)),
            "mean_classifier_l1_delta_from_t0": float(classifier_deltas.mean()),
            "max_classifier_l1_delta_from_t0": float(classifier_deltas.max()),
            "mean_strategy_l1_delta_from_t0": float(strategy_deltas.mean()),
            "max_strategy_l1_delta_from_t0": float(strategy_deltas.max()),
            "mean_confidence": float(confidence.mean()),
            "strategies_sampled": strategies,
        }
    return summary


def _recommend_decision_step(summary_by_step: dict[int, dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        (step, values)
        for step, values in summary_by_step.items()
        if step != 0 and values["mean_classifier_l1_delta_from_t0"] > 0.05
    ]
    if not candidates:
        return {
            "decision_step": None,
            "reason": "No later candidate produced meaningful classifier probability movement versus reset.",
        }
    max_delta = max(values["mean_classifier_l1_delta_from_t0"] for _, values in candidates)
    saturated = [
        (step, values)
        for step, values in candidates
        if values["mean_classifier_l1_delta_from_t0"] >= max_delta * 0.99
    ]
    step, values = min(saturated, key=lambda item: item[0])
    return {
        "decision_step": int(step),
        "reason": "Earliest causal decision point whose classifier movement is within 1% of the strongest observed later signal.",
        "mean_classifier_l1_delta_from_t0": values["mean_classifier_l1_delta_from_t0"],
        "mean_reward": values["mean_reward"],
        "p05_reward": values["p05_reward"],
    }


def _load_selector(path: Path, device: torch.device) -> StrategySelector:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    selector = StrategySelector().to(device)
    selector.load_state_dict(checkpoint["model_state_dict"])
    return selector


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 5A strategy-selection timing diagnostics.")
    parser.add_argument("--decision-steps", nargs="+", type=int, default=[0, 120, 240])
    parser.add_argument("--seed-start", type=int, default=33000)
    parser.add_argument("--classifier", type=Path, default=DEFAULT_CLASSIFIER)
    parser.add_argument("--selector", type=Path, default=DEFAULT_SELECTOR_CHECKPOINT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_OUTPUT_CHECKPOINT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    report = run_strategy_timing_diagnostic(
        decision_steps=tuple(args.decision_steps),
        seed_start=args.seed_start,
        classifier_path=args.classifier,
        selector_checkpoint_path=args.selector,
        output_checkpoint_path=args.checkpoint,
        report_path=args.report,
        require_cuda=not args.allow_cpu,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
