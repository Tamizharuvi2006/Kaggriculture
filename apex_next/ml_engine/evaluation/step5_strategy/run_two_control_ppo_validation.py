"""Controlled 100-episode PPO validation for the bounded two-control target."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, load_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    APEX4_PATH,
    DEFAULT_CLASSIFIER,
    _classifier_probs,
    _load_classifier,
    _opponent_pool,
)
from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import (
    configured_two_control_agent,
)


DECISION_STEP = 120
CONTROL_LIMIT = 0.25
DEFAULT_EPISODES = 100
DEFAULT_SEED_START = 69000
UPDATE_BATCH = 16
PPO_LR = 3e-4
PPO_EPSILON = 0.2


def _flat_params(model: torch.nn.Module) -> torch.Tensor:
    return torch.cat([parameter.detach().flatten() for parameter in model.parameters()])


def _update(
    model,
    optimizer,
    rows: list[dict[str, Any]],
    device: torch.device,
    update_index: int,
    ppo_epochs: int,
) -> dict[str, Any]:
    x = torch.cat([row["x"] for row in rows], dim=0).to(device)
    actions = torch.cat([row["action"] for row in rows], dim=0).to(device)
    old_log_probs = torch.cat([row["old_log_prob"] for row in rows], dim=0).to(device)
    rewards = torch.tensor([row["reward"] for row in rows], dtype=torch.float32, device=device)
    with torch.no_grad():
        _, _, values = model(x)
        advantages = rewards - values.squeeze(-1)
        returns = rewards
        advantage_mean = float(advantages.mean().detach().cpu())
        advantage_std = float(advantages.std(unbiased=False).detach().cpu())
        normalized_advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)

    old_params = _flat_params(model)
    epoch_stats = []
    for _ in range(ppo_epochs):
        distribution, _, values = model.distribution(x)
        new_log_probs = distribution.log_prob(actions).sum(-1)
        ratios = torch.exp(new_log_probs - old_log_probs)
        clipped = ratios.clamp(1.0 - PPO_EPSILON, 1.0 + PPO_EPSILON)
        policy_loss = -torch.minimum(ratios * normalized_advantages, clipped * normalized_advantages).mean()
        value_loss = 0.5 * (values.squeeze(-1) - returns).pow(2).mean()
        entropy = distribution.entropy().sum(-1).mean()
        loss = policy_loss + value_loss - 0.01 * entropy
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).detach().cpu())
        optimizer.step()
        with torch.no_grad():
            approx_kl = float((old_log_probs - new_log_probs).mean().detach().cpu())
            clip_fraction = float(((ratios - 1.0).abs() > PPO_EPSILON).float().mean().detach().cpu())
        epoch_stats.append({
            "policy_loss": float(policy_loss.detach().cpu()),
            "value_loss": float(value_loss.detach().cpu()),
            "entropy": float(entropy.detach().cpu()),
            "approx_kl": approx_kl,
            "clip_fraction": clip_fraction,
            "gradient_norm": gradient_norm,
            "ratio_mean": float(ratios.detach().mean().cpu()),
            "ratio_std": float(ratios.detach().std(unbiased=False).cpu()),
        })
    new_params = _flat_params(model)
    parameter_delta = float((new_params - old_params).abs().max().cpu())
    last = epoch_stats[-1]
    return {
        "update": update_index,
        "episodes": len(rows),
        "advantage_mean": advantage_mean,
        "advantage_std": advantage_std,
        "advantage_min": float(advantages.min().cpu()),
        "advantage_max": float(advantages.max().cpu()),
        "parameter_delta": parameter_delta,
        **last,
        "epochs": epoch_stats,
    }


def _rollout_episode(
    selector: TwoControlSelector,
    classifier: torch.nn.Module,
    classifier_meta: dict[str, Any],
    opponent_fn,
    seed: int,
    episode_index: int,
    device: torch.device,
) -> dict[str, Any]:
    env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
    fixed_agent = load_agent(APEX4_PATH)
    env.reset(seed=seed)
    observation = env.observation(0)
    control_agent = None
    decision = None
    done = False
    steps = 0
    invalid_actions = 0
    while not done:
        if control_agent is None and env.step_count >= DECISION_STEP:
            features = extract_features(observation)
            if features.shape != (128,) or not np.isfinite(features).all():
                raise AssertionError(f"invalid decision features at seed {seed}")
            game_tensor = torch.from_numpy(features).to(device=device, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                opponent_probs = _classifier_probs(classifier, classifier_meta, features, device)
                opponent_tensor = torch.from_numpy(opponent_probs).to(device=device, dtype=torch.float32).unsqueeze(0)
                selector_input = torch.cat([game_tensor, opponent_tensor], dim=-1)
                distribution, confidence, value = selector.distribution(selector_input)
                raw_action = distribution.sample()
                action = raw_action.clamp(-CONTROL_LIMIT, CONTROL_LIMIT)
                log_prob = distribution.log_prob(action).sum(-1)
            controls = action.squeeze(0).detach().cpu().numpy().astype(np.float32)
            control_agent = configured_two_control_agent(float(controls[0]), float(controls[1]), 200000 + episode_index)
            decision = {
                "x": selector_input.detach().cpu(),
                "action": action.detach().cpu(),
                "old_log_prob": log_prob.detach().cpu(),
                "value": float(value.squeeze().cpu()),
                "confidence": float(confidence.squeeze().cpu()),
                "controls": [float(controls[0]), float(controls[1])],
                "opponent_probs": [float(item) for item in opponent_probs],
                "raw_action": [float(item) for item in raw_action.squeeze(0).cpu()],
            }
        active_agent = control_agent or fixed_agent
        action_dict = sanitize_action(call_agent(active_agent, observation, env.configuration))
        if not isinstance(action_dict, dict):
            invalid_actions += 1
        _, _, done, info = env.step(action_dict)
        observation = env.observation(0)
        steps += 1
        if steps > 719:
            raise AssertionError(f"seed {seed} exceeded 719 transitions")

    if decision is None:
        raise AssertionError(f"decision step {DECISION_STEP} not reached for seed {seed}")
    terminal = env.engine.terminal_metrics(0, 0)
    reward = float(terminal["normalized_reward"])
    return {
        "seed": seed,
        "steps": steps,
        "completed": bool(done),
        "reward": reward,
        "win": int(terminal["winner"]) == 0,
        "invalid_actions": invalid_actions,
        "actual_cuda_used": bool(env.actual_cuda_used),
        "device": str(env.engine.money.device),
        "decision": decision,
        "finite": math.isfinite(reward),
        "info_keys": sorted(info.keys()) if isinstance(info, dict) else [],
    }


def run_validation(
    output: Path,
    episodes: int,
    seed_start: int,
    classifier_path: Path,
    init_checkpoint: Path | None = None,
    actor_lr: float = PPO_LR,
    critic_lr: float = PPO_LR,
    ppo_epochs: int = 4,
) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for two-control PPO validation")
    started = time.perf_counter()
    device = torch.device("cuda:0")
    classifier, classifier_meta = _load_classifier(classifier_path, device)
    selector = TwoControlSelector().to(device)
    if init_checkpoint is not None:
        initial = torch.load(init_checkpoint, map_location=device, weights_only=False)
        selector.load_state_dict(initial["model_state_dict"])
    critic_parameters = list(selector.value_head.parameters())
    critic_ids = {id(parameter) for parameter in critic_parameters}
    actor_parameters = [parameter for parameter in selector.parameters() if id(parameter) not in critic_ids]
    optimizer = torch.optim.Adam(
        [
            {"params": actor_parameters, "lr": actor_lr},
            {"params": critic_parameters, "lr": critic_lr},
        ]
    )
    pool = _opponent_pool()
    rows = []
    updates = []
    batch = []
    for episode_index in range(episodes):
        _, opponent_fn = pool[episode_index % len(pool)]
        row = _rollout_episode(selector, classifier, classifier_meta, opponent_fn, seed_start + episode_index, episode_index, device)
        rows.append(row)
        batch.append(row["decision"] | {"reward": row["reward"]})
        if len(batch) >= UPDATE_BATCH or episode_index == episodes - 1:
            updates.append(_update(selector, optimizer, batch, device, len(updates), ppo_epochs))
            batch = []

    controls = np.asarray([row["decision"]["controls"] for row in rows], dtype=np.float32)
    rewards = np.asarray([row["reward"] for row in rows], dtype=np.float32)
    checkpoint_path = output.with_name(f"{output.stem}_selector.pt")
    torch.save(
        {
            "model_state_dict": selector.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "control_range": [-CONTROL_LIMIT, CONTROL_LIMIT],
            "decision_step": DECISION_STEP,
            "episodes": episodes,
        },
        checkpoint_path,
    )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    reloaded = TwoControlSelector()
    reloaded.load_state_dict(checkpoint["model_state_dict"])
    checkpoint_reload = True
    report = {
        "status": "PASS" if all(row["steps"] == 719 and row["completed"] and row["invalid_actions"] == 0 and row["actual_cuda_used"] and row["device"] == "cuda:0" and row["finite"] for row in rows) else "FAIL",
        "validation": "100-episode two-control PPO validation",
        "episodes": episodes,
        "seed_start": seed_start,
        "decision_step": DECISION_STEP,
        "control_range": [-CONTROL_LIMIT, CONTROL_LIMIT],
        "device": str(device),
        "cuda_available": True,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "classifier_device": str(next(classifier.parameters()).device),
        "selector_device": str(next(selector.parameters()).device),
        "engine": "immutable OPT-1 CUDA rollout path",
        "mean_reward": float(rewards.mean()),
        "std_reward": float(rewards.std()),
        "win_rate": float(np.mean([row["win"] for row in rows])),
        "control_distribution": {
            "u_market_mean": float(controls[:, 0].mean()),
            "u_market_std": float(controls[:, 0].std()),
            "u_market_min": float(controls[:, 0].min()),
            "u_market_max": float(controls[:, 0].max()),
            "u_route_mean": float(controls[:, 1].mean()),
            "u_route_std": float(controls[:, 1].std()),
            "u_route_min": float(controls[:, 1].min()),
            "u_route_max": float(controls[:, 1].max()),
        },
        "training": {
            "actor_learning_rate": actor_lr,
            "critic_learning_rate": critic_lr,
            "ppo_epochs": ppo_epochs,
            "initial_checkpoint": str(init_checkpoint) if init_checkpoint else None,
            "clip_epsilon": PPO_EPSILON,
            "updates": updates,
            "final_policy_entropy": updates[-1]["entropy"],
            "final_approx_kl": updates[-1]["approx_kl"],
            "final_clip_fraction": updates[-1]["clip_fraction"],
        },
        "episode_completion": {
            "completed": sum(row["completed"] for row in rows),
            "steps_719": sum(row["steps"] == 719 for row in rows),
            "invalid_actions": sum(row["invalid_actions"] for row in rows),
            "finite_rewards": sum(row["finite"] for row in rows),
        },
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_reload": checkpoint_reload,
        "ppo_updates_started": True,
        "longer_training_started": False,
        "production_modified": False,
        "episode_reports": [
            {key: value for key, value in row.items() if key != "decision"}
            | {"controls": row["decision"]["controls"], "confidence": row["decision"]["confidence"]}
            for row in rows
        ],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=DEFAULT_EPISODES)
    parser.add_argument("--seed-start", type=int, default=DEFAULT_SEED_START)
    parser.add_argument("--classifier", type=Path, default=DEFAULT_CLASSIFIER)
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/two_control_ppo_100_validation.json"))
    parser.add_argument("--init-checkpoint", type=Path, default=None)
    parser.add_argument("--actor-lr", type=float, default=PPO_LR)
    parser.add_argument("--critic-lr", type=float, default=PPO_LR)
    parser.add_argument("--ppo-epochs", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(run_validation(
        args.output,
        args.episodes,
        args.seed_start,
        args.classifier,
        args.init_checkpoint,
        args.actor_lr,
        args.critic_lr,
        args.ppo_epochs,
    ), indent=2))


if __name__ == "__main__":
    main()
