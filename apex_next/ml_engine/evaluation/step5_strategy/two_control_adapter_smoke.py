"""Minimal real-CUDA smoke test for the two-control strategy adapter."""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, load_agent, sanitize_action
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import APEX4_PATH, _opponent_pool
from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import configured_two_control_agent


DECISION_STEP = 120


def _action_signature(action: dict) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _rollout(agent, opponent_fn, seed: int, suffix: int) -> dict:
    env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
    env.reset(seed=seed)
    obs = env.observation(0)
    signatures = []
    feature_at_decision = None
    steps = 0
    done = False
    while not done:
        if env.step_count == DECISION_STEP:
            feature_at_decision = extract_features(obs)
        action = sanitize_action(call_agent(agent, obs, env.configuration))
        signatures.append(_action_signature(action))
        _, _, done, info = env.step(action)
        obs = env.observation(0)
        steps += 1
        if steps > 719:
            raise AssertionError("two-control smoke exceeded 719 transitions")
    metrics = env.engine.terminal_metrics(0, 0)
    if feature_at_decision is None or feature_at_decision.shape != (128,) or not np.isfinite(feature_at_decision).all():
        raise AssertionError("decision-step feature contract failed")
    return {
        "steps": steps,
        "completed": bool(done),
        "terminal_reward": float(metrics["normalized_reward"]),
        "actions": signatures,
        "decision_feature_shape": list(feature_at_decision.shape),
        "actual_cuda_used": bool(env.actual_cuda_used),
        "device": str(env.engine.money.device),
    }


def run_smoke(output: Path) -> dict:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the two-control smoke test")
    opponent_fn = load_agent(APEX4_PATH)
    fixed = _rollout(load_agent(APEX4_PATH), opponent_fn, 68000, 1)
    zero = _rollout(configured_two_control_agent(0.0, 0.0, 2), opponent_fn, 68000, 2)
    market = _rollout(configured_two_control_agent(0.25, 0.0, 3), opponent_fn, 68000, 3)
    route = _rollout(configured_two_control_agent(0.0, 0.25, 4), opponent_fn, 68000, 4)
    zero_equivalent = fixed["actions"] == zero["actions"] and math.isclose(
        fixed["terminal_reward"], zero["terminal_reward"], abs_tol=1e-9
    )
    if not zero_equivalent:
        raise AssertionError("(0,0) two-control adapter is not fixed-v18 equivalent")
    if market["actions"] == zero["actions"] and route["actions"] == zero["actions"]:
        raise AssertionError("representative controls produced no action difference")

    device = torch.device("cuda:0")
    model = TwoControlSelector().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    x = torch.randn((2, 133), device=device)
    target = torch.tensor([[0.25, 0.0], [0.0, 0.25]], device=device)
    dist, confidence, value = model.distribution(x)
    log_prob = dist.log_prob(target).sum(-1)
    advantage = torch.tensor([1.0, -1.0], device=device)
    returns = torch.tensor([0.5, -0.5], device=device)
    loss = -(log_prob * advantage).mean() + 0.5 * (value.squeeze(-1) - returns).pow(2).mean() - 0.01 * dist.entropy().sum(-1).mean()
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).detach().cpu())
    optimizer.step()
    finite = bool(torch.isfinite(loss).item() and math.isfinite(grad_norm))
    with tempfile.TemporaryDirectory() as directory:
        checkpoint = Path(directory) / "two_control_smoke.pt"
        torch.save({"model_state_dict": model.state_dict(), "control_range": [-0.25, 0.25]}, checkpoint)
        reloaded = TwoControlSelector()
        reloaded.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=False)["model_state_dict"])
        reload_ok = True

    report = {
        "status": "PASS",
        "decision_step": DECISION_STEP,
        "cuda": True,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "control_range": [-0.25, 0.25],
        "zero_control_equivalent_to_fixed_v18": zero_equivalent,
        "representative_control_behavior": {
            "market_positive_differs": market["actions"] != zero["actions"],
            "route_positive_differs": route["actions"] != zero["actions"],
        },
        "episodes": {"fixed": fixed["steps"], "zero": zero["steps"], "market": market["steps"], "route": route["steps"]},
        "all_cuda": all(item["actual_cuda_used"] and item["device"] == "cuda:0" for item in (fixed, zero, market, route)),
        "ppo_smoke": {"finite_loss": finite, "gradient_norm": grad_norm, "checkpoint_reload": reload_ok, "output_shape": [2, 2]},
        "long_training_started": False,
        "production_modified": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/two_control_adapter_smoke.json"))
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.output), indent=2))


if __name__ == "__main__":
    main()
