"""Frozen common-seed evaluation for fixed-v18 versus the trained selector."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
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


def _run_one(
    mode: str,
    seed: int,
    episode_index: int,
    opponent_fn,
    selector: TwoControlSelector | None,
    classifier: torch.nn.Module,
    classifier_meta: dict[str, Any],
    device: torch.device,
) -> dict[str, Any]:
    env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
    fixed_agent = load_agent(APEX4_PATH)
    env.reset(seed=seed)
    observation = env.observation(0)
    control_agent = None
    controls = [0.0, 0.0]
    done = False
    steps = 0
    invalid_actions = 0

    while not done:
        if control_agent is None and env.step_count >= DECISION_STEP:
            if mode == "ppo":
                features = extract_features(observation)
                if features.shape != (128,) or not np.isfinite(features).all():
                    raise AssertionError(f"invalid decision features at seed {seed}")
                with torch.no_grad():
                    game_tensor = torch.from_numpy(features).to(device=device, dtype=torch.float32).unsqueeze(0)
                    probs = _classifier_probs(classifier, classifier_meta, features, device)
                    opponent_tensor = torch.from_numpy(probs).to(device=device, dtype=torch.float32).unsqueeze(0)
                    selector_input = torch.cat([game_tensor, opponent_tensor], dim=-1)
                    predicted, _, _ = selector(selector_input)
                controls = predicted.squeeze(0).detach().cpu().numpy().astype(np.float32).tolist()
            control_agent = configured_two_control_agent(
                float(np.clip(controls[0], -CONTROL_LIMIT, CONTROL_LIMIT)),
                float(np.clip(controls[1], -CONTROL_LIMIT, CONTROL_LIMIT)),
                300000 + episode_index,
            )

        active_agent = control_agent or fixed_agent
        action = sanitize_action(call_agent(active_agent, observation, env.configuration))
        if not isinstance(action, dict):
            invalid_actions += 1
        _, _, done, _ = env.step(action)
        observation = env.observation(0)
        steps += 1
        if steps > 719:
            raise AssertionError(f"seed {seed} exceeded 719 transitions")

    terminal = env.engine.terminal_metrics(0, 0)
    reward = float(terminal["normalized_reward"])
    winner = terminal.get("winner")
    return {
        "mode": mode,
        "seed": seed,
        "steps": steps,
        "completed": bool(done),
        "reward": reward,
        "win": bool(int(winner) == 0) if winner is not None else bool(reward > 0.0),
        "controls": [float(controls[0]), float(controls[1])],
        "invalid_actions": invalid_actions,
        "actual_cuda_used": bool(env.actual_cuda_used),
        "device": str(env.engine.money.device),
        "terminal_metrics": terminal,
        "finite": math.isfinite(reward),
    }


def run_evaluation(output: Path, checkpoint: Path, seed_start: int, episodes: int) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for frozen evaluation")
    device = torch.device("cuda:0")
    classifier, classifier_meta = _load_classifier(DEFAULT_CLASSIFIER, device)
    selector = TwoControlSelector().to(device)
    checkpoint_data = torch.load(checkpoint, map_location=device, weights_only=False)
    selector.load_state_dict(checkpoint_data["model_state_dict"])
    selector.eval()
    pool = _opponent_pool()
    results = {"fixed_v18": [], "ppo": []}
    for index in range(episodes):
        _, opponent_fn = pool[index % len(pool)]
        seed = seed_start + index
        results["fixed_v18"].append(_run_one("fixed_v18", seed, index, opponent_fn, None, classifier, classifier_meta, device))
        results["ppo"].append(_run_one("ppo", seed, index, opponent_fn, selector, classifier, classifier_meta, device))

    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        rewards = np.asarray([row["reward"] for row in rows], dtype=np.float32)
        controls = np.asarray([row["controls"] for row in rows], dtype=np.float32)
        return {
            "episodes": len(rows),
            "mean_reward": float(rewards.mean()),
            "std_reward": float(rewards.std()),
            "p05_reward": float(np.quantile(rewards, 0.05)),
            "p95_reward": float(np.quantile(rewards, 0.95)),
            "win_rate": float(np.mean([row["win"] for row in rows])),
            "u_market_mean": float(controls[:, 0].mean()),
            "u_market_std": float(controls[:, 0].std()),
            "u_route_mean": float(controls[:, 1].mean()),
            "u_route_std": float(controls[:, 1].std()),
            "completed": sum(row["completed"] for row in rows),
            "steps_719": sum(row["steps"] == 719 for row in rows),
            "invalid_actions": sum(row["invalid_actions"] for row in rows),
            "actual_cuda_used": all(row["actual_cuda_used"] and row["device"] == "cuda:0" for row in rows),
        }

    paired_delta = [b["reward"] - a["reward"] for a, b in zip(results["fixed_v18"], results["ppo"])]
    report = {
        "status": "PASS",
        "evaluation": "frozen common-seed fixed-v18 versus PPO checkpoint",
        "seed_start": seed_start,
        "episodes": episodes,
        "decision_step": DECISION_STEP,
        "checkpoint": str(checkpoint),
        "checkpoint_updates": False,
        "device": str(device),
        "cuda_device_name": torch.cuda.get_device_name(0),
        "summary": {mode: summary(rows) for mode, rows in results.items()},
        "paired_reward_delta_ppo_minus_fixed": {
            "mean": float(np.mean(paired_delta)),
            "std": float(np.std(paired_delta)),
            "ppo_higher": sum(delta > 0 for delta in paired_delta),
            "fixed_higher": sum(delta < 0 for delta in paired_delta),
            "ties": sum(delta == 0 for delta in paired_delta),
        },
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=77000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/frozen_common_seed_evaluation.json"))
    args = parser.parse_args()
    print(json.dumps(run_evaluation(args.output, args.checkpoint, args.seed_start, args.episodes), indent=2))


if __name__ == "__main__":
    main()
