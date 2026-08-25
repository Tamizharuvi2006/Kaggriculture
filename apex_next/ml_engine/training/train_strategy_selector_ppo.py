"""Step 5 PPO smoke trainer for the APEX 4.1 strategy selector."""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, load_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.models.strategy_selector import StrategySelector
from apex_next.ml_engine.training.targeted_opponents import (
    aggressive_expand_agent,
    crop_heavy_agent,
    market_manipulator_agent,
)
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
APEX4_PATH = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
APEX35_PATH = PROJECT_ROOT / "submission.py"
V18_PATH = PROJECT_ROOT / "baseline" / "kaitofukami-v18.py"
DEFAULT_CLASSIFIER = ML_ENGINE_DIR / "checkpoints" / "opponent_classifier" / "opponent_classifier.pt"
DEFAULT_CHECKPOINT = ML_ENGINE_DIR / "checkpoints" / "strategy_selector" / "strategy_selector_smoke.pt"
DEFAULT_REPORT = ML_ENGINE_DIR / "evaluation" / "step5_strategy" / "strategy_selector_smoke_report.json"

AgentFn = Callable[[dict[str, Any], Any], dict[str, list[Any]]]

PPO_CONFIG = {
    "lr": 3e-4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_epsilon": 0.2,
    "epochs_per_update": 4,
    "batch_size": 64,
}

STRATEGY_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "name": "PREMIUM",
        "overrides": {"cows": 8, "sheep": 6, "cash_reserve": 250, "animal_daily_cap": 3, "force_expert": "PREMIUM_CROP"},
    },
    {
        "name": "LIVESTOCK",
        "overrides": {"cows": 12, "sheep": 2, "cash_reserve": 150, "animal_daily_cap": 3, "force_expert": "COW_RUSH"},
    },
    {
        "name": "WHEAT_RUSH",
        "overrides": {"cows": 12, "sheep": 2, "cash_reserve": 150, "animal_daily_cap": 1, "force_expert": "WHEAT_RUSH"},
    },
    {
        "name": "BALANCED",
        "overrides": {"cows": 8, "sheep": 6, "cash_reserve": 150, "animal_daily_cap": 3, "force_expert": None},
    },
)

def train_strategy_selector_ppo_smoke(
    classifier_path: Path = DEFAULT_CLASSIFIER,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    report_path: Path = DEFAULT_REPORT,
    episodes: int = 4,
    seed_start: int = 30000,
    decision_step: int = 120,
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Run a tiny real-environment PPO smoke test."""

    started = time.perf_counter()
    _seed_everything(5105)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if require_cuda and device.type != "cuda":
        raise RuntimeError("CUDA is required for Step 5 smoke training but torch.cuda.is_available() is False")

    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = StrategySelector().to(device)
    optimizer = torch.optim.Adam(selector.parameters(), lr=PPO_CONFIG["lr"])

    device_checks = {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "selected_device": str(device),
        "classifier_device": str(next(classifier.parameters()).device),
        "selector_device": str(next(selector.parameters()).device),
    }
    if require_cuda and not all(value.startswith("cuda") for key, value in device_checks.items() if key.endswith("_device")):
        raise RuntimeError(f"Step 5 models are not on CUDA: {device_checks}")

    opponent_pool = _opponent_pool()
    trajectories: list[dict[str, Any]] = []
    episode_reports: list[dict[str, Any]] = []

    for episode in range(episodes):
        seed = seed_start + episode
        opponent_id, opponent_fn = opponent_pool[episode % len(opponent_pool)]
        env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
        obs_features = env.reset(seed=seed)
        default_agent = _configured_apex4_agent({}, module_suffix=episode)
        selected_agent = None
        decision_record = None

        done = False
        reward = 0.0
        steps = 0
        invalid_features = 0
        while not done:
            obs = env.observation(0)
            features = extract_features(obs)
            if features.shape != (128,) or features.dtype != np.float32 or not np.isfinite(features).all():
                invalid_features += 1
            if decision_record is None and env.step_count >= decision_step:
                opp_probs = _classifier_probs(classifier, classifier_meta, features, device)
                x = _selector_input(features, opp_probs, device)
                distribution, confidence, value = selector.distribution(x)
                strategy_idx = distribution.sample()
                log_prob = distribution.log_prob(strategy_idx)
                strategy_weights = distribution.probs.detach().cpu().numpy()[0]
                confidence_value = float(confidence.detach().cpu().item())
                selected_profile = STRATEGY_PROFILES[int(strategy_idx.item())]
                strategy_name = selected_profile["name"]
                selected_agent = _configured_apex4_agent(selected_profile["overrides"], module_suffix=episode)
                decision_record = {
                    "state": x,
                    "action": strategy_idx,
                    "old_log_prob": log_prob,
                    "strategy_index": int(strategy_idx.item()),
                    "strategy_name": strategy_name,
                    "strategy_weights": strategy_weights,
                    "confidence": confidence_value,
                    "decision_uses_observation_step": int(env.step_count),
                }
            active_agent = selected_agent if selected_agent is not None else default_agent
            action = sanitize_action(call_agent(active_agent, obs, env.configuration))
            next_features, reward, done, info = env.step(action)
            if next_features.shape != (128,) or next_features.dtype != np.float32 or not np.isfinite(next_features).all():
                invalid_features += 1
            steps = int(info["step"])
            if steps > 720:
                raise AssertionError(f"Step 5 smoke episode exceeded 720 steps: {steps}")

        if decision_record is None:
            raise AssertionError(f"decision step {decision_step} was never reached")
        normalized_reward = float(reward) / 100000.0
        x = decision_record["state"]
        strategy_idx = decision_record["action"]
        log_prob = decision_record["old_log_prob"]
        trajectories.append(
            {
                "state": x.detach().squeeze(0),
                "action": strategy_idx.detach().squeeze(0),
                "old_log_prob": log_prob.detach().squeeze(0),
                "reward": normalized_reward,
            }
        )
        episode_reports.append(
            {
                "episode": episode,
                "seed": seed,
                "opponent_id": opponent_id,
                "strategy_index": decision_record["strategy_index"],
                "strategy_name": decision_record["strategy_name"],
                "strategy_weights": [float(item) for item in decision_record["strategy_weights"]],
                "strategy_weight_sum": float(decision_record["strategy_weights"].sum()),
                "confidence": decision_record["confidence"],
                "decision_step": int(decision_record["decision_uses_observation_step"]),
                "raw_terminal_reward": float(reward),
                "normalized_reward": normalized_reward,
                "steps": steps,
                "completed": bool(done),
                "invalid_feature_count": invalid_features,
            }
        )

    old_params = _flat_params(selector)
    update_stats = _ppo_update(selector, optimizer, trajectories, device)
    new_params = _flat_params(selector)
    max_param_delta = float((new_params - old_params).abs().max().detach().cpu().item())

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": selector.state_dict(),
            "ppo_config": PPO_CONFIG,
            "strategy_profiles": STRATEGY_PROFILES,
            "classifier_path": str(classifier_path),
            "smoke_report_path": str(report_path),
        },
        checkpoint_path,
    )
    reload_ok = _verify_checkpoint_reload(checkpoint_path)
    unique_opponents = sorted({episode["opponent_id"] for episode in episode_reports})

    report = {
        "status": "PASS"
        if _smoke_passed(episode_reports, update_stats, max_param_delta, reload_ok, len(opponent_pool))
        else "FAIL",
        "step": "STEP 5 - Strategy Selector PPO smoke",
        "mode": "smoke",
        "episodes": episodes,
        "source_classifier": str(classifier_path),
        "checkpoint_path": str(checkpoint_path),
        "architecture": "133 -> 64 -> 32 -> strategy(4), confidence(1), value(1)",
        "ppo_config": PPO_CONFIG,
        "decision_step": decision_step,
        "engine": "immutable OPT-1 CUDA snapshot",
        "device": device_checks,
        "classifier_inference_check": classifier_meta["inference_check"],
        "opponent_pool": [name for name, _ in opponent_pool],
        "opponents_exercised": unique_opponents,
        "opponent_pool_coverage": {
            "unique_exercised": len(unique_opponents),
            "pool_size": len(opponent_pool),
            "covered_all_available": len(unique_opponents) == min(episodes, len(opponent_pool)),
        },
        "strategy_profiles": [profile["name"] for profile in STRATEGY_PROFILES],
        "reward_definition": "terminal (our_MCV - opponent_MCV) / 100000.0",
        "update_stats": update_stats,
        "max_parameter_delta": max_param_delta,
        "checkpoint_reload_ok": reload_ok,
        "episode_reports": episode_reports,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _ppo_update(
    selector: StrategySelector,
    optimizer: torch.optim.Optimizer,
    trajectories: list[dict[str, Any]],
    device: torch.device,
) -> dict[str, Any]:
    rewards = torch.tensor([item["reward"] for item in trajectories], dtype=torch.float32, device=device)
    states = torch.stack([item["state"] for item in trajectories]).to(device)
    actions = torch.stack([item["action"] for item in trajectories]).to(device)
    old_log_probs = torch.stack([item["old_log_prob"] for item in trajectories]).to(device)
    old_strategy_probs = None
    if all("old_strategy_probs" in item for item in trajectories):
        old_strategy_probs = torch.stack([item["old_strategy_probs"] for item in trajectories]).to(device)
    with torch.no_grad():
        _, _, initial_values = selector.distribution(states)
    returns = rewards
    values = initial_values.squeeze(-1)
    advantages = returns - values.detach()
    if advantages.numel() > 1:
        advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)

    raw_advantages = returns - values.detach()
    update_start_params = _flat_params(selector).detach().clone()
    advantage_diagnostics = {
        "mean": float(raw_advantages.mean().detach().cpu().item()),
        "std": float(raw_advantages.std(unbiased=False).detach().cpu().item()),
        "min": float(raw_advantages.min().detach().cpu().item()),
        "max": float(raw_advantages.max().detach().cpu().item()),
        "normalized_mean": float(advantages.mean().detach().cpu().item()),
        "normalized_std": float(advantages.std(unbiased=False).detach().cpu().item()),
    }

    losses: list[float] = []
    policy_losses: list[float] = []
    value_losses: list[float] = []
    entropy_values: list[float] = []
    update_diagnostics: list[dict[str, Any]] = []

    # One decision per episode in the smoke; repeat PPO epochs over the tiny batch.
    for _ in range(PPO_CONFIG["epochs_per_update"]):
        distribution, _, current_values_raw = selector.distribution(states)
        log_probs = distribution.log_prob(actions)
        current_values = current_values_raw.squeeze(-1)
        entropy = distribution.entropy().mean()
        ratio = torch.exp(log_probs - old_log_probs)
        unclipped = ratio * advantages
        clipped = torch.clamp(ratio, 1.0 - PPO_CONFIG["clip_epsilon"], 1.0 + PPO_CONFIG["clip_epsilon"]) * advantages
        policy_loss = -torch.min(unclipped, clipped).mean()
        value_loss = nn.functional.mse_loss(current_values, returns)
        loss = policy_loss + 0.5 * value_loss - 0.01 * entropy

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        actor_grad_sq = torch.zeros((), dtype=torch.float32, device=device)
        strategy_head_grad_sq = torch.zeros((), dtype=torch.float32, device=device)
        for name, parameter in selector.named_parameters():
            if parameter.grad is None:
                continue
            grad_sq = parameter.grad.detach().float().pow(2).sum()
            if name.startswith("shared.") or name.startswith("strategy_head."):
                actor_grad_sq = actor_grad_sq + grad_sq
            if name.startswith("strategy_head."):
                strategy_head_grad_sq = strategy_head_grad_sq + grad_sq
        grad_norm = float(torch.nn.utils.clip_grad_norm_(selector.parameters(), max_norm=1.0).detach().cpu().item())
        optimizer.step()

        with torch.no_grad():
            current_probs = distribution.probs.detach()
            approx_kl = (old_log_probs - log_probs.detach()).mean()
            clip_fraction = ((ratio.detach() - 1.0).abs() > PPO_CONFIG["clip_epsilon"]).float().mean()
            exact_kl = None
            if old_strategy_probs is not None:
                safe_old_probs = old_strategy_probs.clamp_min(1e-8)
                safe_new_probs = current_probs.clamp_min(1e-8)
                exact_kl = (safe_old_probs * (safe_old_probs.log() - safe_new_probs.log())).sum(dim=-1).mean()
            post_update_params = _flat_params(selector).detach()
            delta = post_update_params - update_start_params
            diagnostic = {
                "epoch": len(update_diagnostics),
                "approx_kl": float(approx_kl.cpu().item()),
                "exact_kl": float(exact_kl.cpu().item()) if exact_kl is not None else None,
                "clip_fraction": float(clip_fraction.cpu().item()),
                "ratio_mean": float(ratio.detach().mean().cpu().item()),
                "ratio_std": float(ratio.detach().std(unbiased=False).cpu().item()),
                "ratio_min": float(ratio.detach().min().cpu().item()),
                "ratio_max": float(ratio.detach().max().cpu().item()),
                "old_log_prob_mean": float(old_log_probs.mean().cpu().item()),
                "old_log_prob_std": float(old_log_probs.std(unbiased=False).cpu().item()),
                "new_log_prob_mean": float(log_probs.detach().mean().cpu().item()),
                "new_log_prob_std": float(log_probs.detach().std(unbiased=False).cpu().item()),
                "advantage_mean": advantage_diagnostics["mean"],
                "advantage_std": advantage_diagnostics["std"],
                "advantage_min": advantage_diagnostics["min"],
                "advantage_max": advantage_diagnostics["max"],
                "normalized_advantage_mean": advantage_diagnostics["normalized_mean"],
                "normalized_advantage_std": advantage_diagnostics["normalized_std"],
                "policy_entropy": float(entropy.detach().cpu().item()),
                "gradient_norm": grad_norm,
                "actor_gradient_norm": float(torch.sqrt(actor_grad_sq).cpu().item()),
                "strategy_head_gradient_norm": float(torch.sqrt(strategy_head_grad_sq).cpu().item()),
                "parameter_delta_max": float(delta.abs().max().cpu().item()),
                "parameter_delta_l2": float(torch.linalg.vector_norm(delta).cpu().item()),
                "policy_loss": float(policy_loss.detach().cpu().item()),
                "value_loss": float(value_loss.detach().cpu().item()),
                "old_action_probability_mean": float(torch.exp(old_log_probs).mean().cpu().item()),
                "new_action_probability_mean": float(torch.exp(log_probs.detach()).mean().cpu().item()),
                "new_strategy_probs_mean": [float(value) for value in current_probs.mean(dim=0).cpu().tolist()],
            }
            if old_strategy_probs is not None:
                diagnostic["old_strategy_probs_mean"] = [
                    float(value) for value in old_strategy_probs.mean(dim=0).cpu().tolist()
                ]
            update_diagnostics.append(diagnostic)

        losses.append(float(loss.detach().cpu().item()))
        policy_losses.append(float(policy_loss.detach().cpu().item()))
        value_losses.append(float(value_loss.detach().cpu().item()))
        entropy_values.append(float(entropy.detach().cpu().item()))

    finite = all(np.isfinite(losses)) and all(np.isfinite(policy_losses)) and all(np.isfinite(value_losses))
    return {
        "ppo_epochs": PPO_CONFIG["epochs_per_update"],
        "losses": losses,
        "policy_losses": policy_losses,
        "value_losses": value_losses,
        "entropy": entropy_values,
        "grad_norm_last": grad_norm,
        "finite_losses": bool(finite),
        "reward_mean": float(rewards.mean().detach().cpu().item()),
        "reward_min": float(rewards.min().detach().cpu().item()),
        "reward_max": float(rewards.max().detach().cpu().item()),
        "advantage_diagnostics": advantage_diagnostics,
        "update_diagnostics": update_diagnostics,
        "approx_kl_last": update_diagnostics[-1]["approx_kl"],
        "exact_kl_last": update_diagnostics[-1]["exact_kl"],
        "clip_fraction_last": update_diagnostics[-1]["clip_fraction"],
        "ratio_diagnostics_last": {
            key: update_diagnostics[-1][key]
            for key in ("ratio_mean", "ratio_std", "ratio_min", "ratio_max")
        },
        "log_prob_diagnostics_last": {
            key: update_diagnostics[-1][key]
            for key in ("old_log_prob_mean", "old_log_prob_std", "new_log_prob_mean", "new_log_prob_std")
        },
        "optimizer_diagnostics": {
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "batch_size": int(rewards.numel()),
            "ppo_epochs": int(PPO_CONFIG["epochs_per_update"]),
            "clip_epsilon": float(PPO_CONFIG["clip_epsilon"]),
        },
        "actor_gradient_norm_last": update_diagnostics[-1]["actor_gradient_norm"],
        "strategy_head_gradient_norm_last": update_diagnostics[-1]["strategy_head_gradient_norm"],
        "parameter_delta_from_update_start_max": update_diagnostics[-1]["parameter_delta_max"],
        "parameter_delta_from_update_start_l2": update_diagnostics[-1]["parameter_delta_l2"],
    }


def _load_classifier(path: Path, device: torch.device) -> tuple[OpponentClassifier, dict[str, Any]]:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    classifier = OpponentClassifier().to(device)
    classifier.load_state_dict(checkpoint["model_state_dict"])
    classifier.eval()
    feature_mean = torch.tensor(checkpoint["feature_mean"], dtype=torch.float32, device=device)
    feature_std = torch.tensor(checkpoint["feature_std"], dtype=torch.float32, device=device)

    dummy_features = np.zeros(128, dtype=np.float32)
    probs = _classifier_probs(classifier, {"feature_mean": feature_mean, "feature_std": feature_std}, dummy_features, device)
    inference_check = {
        "shape": list(probs.shape),
        "sum": float(probs.sum()),
        "finite": bool(np.isfinite(probs).all()),
        "min": float(probs.min()),
        "max": float(probs.max()),
    }
    return classifier, {"feature_mean": feature_mean, "feature_std": feature_std, "inference_check": inference_check}


def _classifier_probs(
    classifier: OpponentClassifier,
    classifier_meta: dict[str, Any],
    features_128: np.ndarray,
    device: torch.device,
) -> np.ndarray:
    opponent_slice = torch.tensor(features_128[60:84], dtype=torch.float32, device=device)
    x = ((opponent_slice - classifier_meta["feature_mean"]) / classifier_meta["feature_std"]).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(classifier(x), dim=-1).squeeze(0).detach().cpu().numpy()
    if probs.shape != (5,) or not np.isfinite(probs).all():
        raise AssertionError(f"invalid classifier probabilities: shape={probs.shape}, values={probs}")
    return probs.astype(np.float32, copy=False)


def _selector_input(features_128: np.ndarray, opp_probs_5: np.ndarray, device: torch.device) -> torch.Tensor:
    if features_128.shape != (128,) or opp_probs_5.shape != (5,):
        raise AssertionError(f"expected selector input pieces (128,) and (5,), got {features_128.shape}, {opp_probs_5.shape}")
    x = np.concatenate([features_128.astype(np.float32, copy=False), opp_probs_5.astype(np.float32, copy=False)])
    if x.shape != (133,) or not np.isfinite(x).all():
        raise AssertionError("selector input must be finite shape (133,)")
    return torch.tensor(x, dtype=torch.float32, device=device).unsqueeze(0)


def _configured_apex4_agent(overrides: dict[str, Any], module_suffix: int) -> AgentFn:
    module_name = f"apex4_strategy_selector_smoke_{module_suffix}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, APEX4_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load APEX4 agent from {APEX4_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The sealed APEX4 submission defaults to its fixed v18 schedule. PPO's
    # strategy profiles must exercise the configurable policy path so their
    # profile fields and force_expert setting can affect executable actions.
    strategy_overrides = dict(overrides)
    strategy_overrides["use_fixed_schedule"] = False
    module.configure_strategy(strategy_overrides)

    # The shared early maintenance route can consume the order cap before a
    # selected expert's defining purchase is emitted. Keep the sealed APEX4
    # module untouched and make only the PPO strategy adapter preserve the
    # profile's early identity at the action boundary.
    profile_force = strategy_overrides.get("force_expert")
    base_agent = module.agent

    def configured_agent(obs: dict[str, Any], configuration: Any = None) -> dict[str, Any]:
        action = base_agent(obs, configuration)
        if not isinstance(action, dict):
            return action
        step = int(obs.get("step", 0)) if isinstance(obs, dict) else 0
        if step > 4:
            return action
        market = [list(order) for order in (action.get("market") or [])]
        if profile_force == "COW_RUSH" and not any(order[:2] == ["BUY_ANIMAL", "COW"] for order in market if len(order) >= 2):
            replacement = next((idx for idx, order in enumerate(market) if order and order[0] == "BUY_SEED"), None)
            if replacement is not None:
                market[replacement] = ["BUY_ANIMAL", "COW", 1]
        elif profile_force == "WHEAT_RUSH":
            wheat_seed = next((order for order in market if len(order) >= 2 and order[:2] == ["BUY_SEED", "WHEAT"]), None)
            if wheat_seed is not None and len(wheat_seed) >= 3:
                wheat_seed[2] = max(int(wheat_seed[2]), 4)
        action["market"] = market
        return action

    return configured_agent


def _opponent_pool() -> list[tuple[str, AgentFn]]:
    pool: list[tuple[str, AgentFn]] = [
        ("apex4", load_agent(APEX4_PATH)),
        ("baseline_v18", load_agent(V18_PATH)),
        ("crop_heavy_targeted", crop_heavy_agent),
        ("aggressive_expand_targeted", aggressive_expand_agent),
        ("market_manipulator_targeted", market_manipulator_agent),
    ]
    if APEX35_PATH.exists():
        pool.insert(0, ("apex35_live", load_agent(APEX35_PATH)))
    return pool


def _smoke_passed(
    episode_reports: list[dict[str, Any]],
    update_stats: dict[str, Any],
    max_param_delta: float,
    reload_ok: bool,
    opponent_pool_size: int,
) -> bool:
    if not episode_reports:
        return False
    for report in episode_reports:
        weights = np.asarray(report["strategy_weights"], dtype=np.float32)
        if report["steps"] != 719 or not report["completed"]:
            return False
        if report["invalid_feature_count"] != 0:
            return False
        if weights.shape != (4,) or not np.isfinite(weights).all():
            return False
        if not np.isclose(weights.sum(), 1.0, atol=1e-5):
            return False
        if not 0.0 <= float(report["confidence"]) <= 1.0:
            return False
        if not np.isfinite(float(report["normalized_reward"])):
            return False
    unique_opponents = {report["opponent_id"] for report in episode_reports}
    opponent_coverage_ok = len(unique_opponents) == min(len(episode_reports), opponent_pool_size)
    return bool(update_stats["finite_losses"] and max_param_delta > 0.0 and reload_ok and opponent_coverage_ok)


def _verify_checkpoint_reload(path: Path) -> bool:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    selector = StrategySelector()
    selector.load_state_dict(checkpoint["model_state_dict"])
    x = torch.zeros((2, 133), dtype=torch.float32)
    weights, confidence, value = selector(x)
    return bool(weights.shape == (2, 4) and confidence.shape == (2, 1) and value.shape == (2, 1))


def _flat_params(model: nn.Module) -> torch.Tensor:
    return torch.cat([param.detach().flatten() for param in model.parameters()])


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small Step 5 PPO strategy selector smoke test.")
    parser.add_argument("--episodes", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=30000)
    parser.add_argument("--decision-step", type=int, default=120)
    parser.add_argument("--classifier", type=Path, default=DEFAULT_CLASSIFIER)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    report = train_strategy_selector_ppo_smoke(
        classifier_path=args.classifier,
        checkpoint_path=args.checkpoint,
        report_path=args.report,
        episodes=args.episodes,
        seed_start=args.seed_start,
        decision_step=args.decision_step,
        require_cuda=not args.allow_cpu,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
