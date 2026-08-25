"""Production-readiness checks for the frozen Step 5B candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
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
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    APEX4_PATH,
    DEFAULT_CLASSIFIER,
    _classifier_probs,
    _load_classifier,
    _opponent_pool,
)
from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import configured_two_control_agent


DECISION_STEP = 120
CONTROL_LIMIT = 0.25


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _rollout(checkpoint: Path, seed: int, opponent_fn, episode_index: int) -> dict:
    device = torch.device("cuda:0")
    classifier, classifier_meta = _load_classifier(DEFAULT_CLASSIFIER, device)
    selector = TwoControlSelector().to(device)
    state = torch.load(checkpoint, map_location=device, weights_only=False)
    selector.load_state_dict(state["model_state_dict"])
    selector.eval()
    for parameter in selector.parameters():
        parameter.requires_grad_(False)

    env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
    fixed_agent = load_agent(APEX4_PATH)
    env.reset(seed=seed)
    observation = env.observation(0)
    control_agent = None
    controls = None
    action_trace = []
    decision_step_seen = None
    done = False
    steps = 0
    invalid_actions = 0
    with torch.inference_mode():
        while not done:
            if control_agent is None and env.step_count >= DECISION_STEP:
                decision_step_seen = env.step_count
                features = extract_features(observation)
                if features.shape != (128,) or not np.isfinite(features).all():
                    raise AssertionError("invalid decision features")
                game = torch.from_numpy(features).to(device=device, dtype=torch.float32).unsqueeze(0)
                probs = _classifier_probs(classifier, classifier_meta, features, device)
                opponent = torch.from_numpy(probs).to(device=device, dtype=torch.float32).unsqueeze(0)
                predicted, _, _ = selector(torch.cat([game, opponent], dim=-1))
                controls = predicted.squeeze(0).detach().cpu().numpy().astype(np.float32)
                if not np.all(np.isfinite(controls)) or np.any(np.abs(controls) > CONTROL_LIMIT + 1e-6):
                    raise AssertionError("control contract violated")
                control_agent = configured_two_control_agent(
                    float(controls[0]), float(controls[1]), 400000 + episode_index
                )

            active_agent = control_agent or fixed_agent
            action = sanitize_action(call_agent(active_agent, observation, env.configuration))
            if not isinstance(action, dict):
                invalid_actions += 1
            action_trace.append(_jsonable(action))
            _, _, done, _ = env.step(action)
            observation = env.observation(0)
            steps += 1
            if steps > 719:
                raise AssertionError("trajectory exceeded 719 steps")

    terminal = env.engine.terminal_metrics(0, 0)
    return {
        "seed": seed,
        "steps": steps,
        "completed": bool(done),
        "decision_step": decision_step_seen,
        "controls": controls.tolist() if controls is not None else None,
        "invalid_actions": invalid_actions,
        "actual_cuda_used": bool(env.actual_cuda_used),
        "device": str(env.engine.money.device),
        "terminal_metrics": _jsonable(terminal),
        "action_trace": action_trace,
    }


def run(output: Path, checkpoint: Path, seed: int) -> dict:
    manifest_path = checkpoint.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hash = manifest["sha256"]
    actual_hash = _sha256(checkpoint)
    hash_pass = actual_hash == expected_hash
    required = [checkpoint, manifest_path, DEFAULT_CLASSIFIER, Path(APEX4_PATH)]
    packaging = {str(path): path.exists() for path in required}

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for production-readiness validation")
    pool = _opponent_pool()
    opponent_fn = pool[0][1]
    first = _rollout(checkpoint, seed, opponent_fn, 1)
    second = _rollout(checkpoint, seed, opponent_fn, 1)
    reproducible = (
        first["controls"] == second["controls"]
        and first["action_trace"] == second["action_trace"]
        and first["terminal_metrics"] == second["terminal_metrics"]
    )
    correctness = (
        first["completed"]
        and second["completed"]
        and first["steps"] == second["steps"] == 719
        and first["invalid_actions"] == second["invalid_actions"] == 0
        and first["actual_cuda_used"]
        and second["actual_cuda_used"]
    )
    interface = (
        first["controls"] is not None
        and len(first["controls"]) == 2
        and all(-CONTROL_LIMIT <= value <= CONTROL_LIMIT for value in first["controls"])
    )
    timing = first["decision_step"] == second["decision_step"] == DECISION_STEP
    gates = {
        "checkpoint_hash": hash_pass,
        "clean_inference_load": True,
        "inference_only": True,
        "two_control_interface": interface,
        "decision_step_120": timing,
        "same_seed_reproducibility": reproducible,
        "719_step_cuda_safety": correctness,
        "packaging_required_files": all(packaging.values()),
    }
    report = {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256_expected": expected_hash,
        "checkpoint_sha256_actual": actual_hash,
        "device": "cuda:0",
        "cuda_device_name": torch.cuda.get_device_name(0),
        "seed": seed,
        "packaging_files": packaging,
        "production_promoted": False,
        "first_run": {key: value for key, value in first.items() if key != "action_trace"},
        "repeated_run": {key: value for key, value in second.items() if key != "action_trace"},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=77200)
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/production_readiness.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.checkpoint, args.seed), indent=2))


if __name__ == "__main__":
    main()
