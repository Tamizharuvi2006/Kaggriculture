"""Find the first post-decision trajectory divergence between research and package paths."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import configured_two_control_agent
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector
from apex_next.ml_engine.training.train_strategy_selector_ppo import (
    DEFAULT_CLASSIFIER,
    _classifier_probs,
    _load_classifier,
)

DECISION_STEP = 120


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _entry_signature(entry: dict[str, Any]) -> dict[str, Any]:
    observation = entry.get("observation", {})
    action = entry.get("action")
    return {
        "action": action,
        "observation_json": _stable(observation),
        "status": entry.get("status"),
        "reward": entry.get("reward"),
    }


def _research_agent_factory(sealed, selector, classifier, classifier_meta, device, seed: int):
    fixed_agent = sealed.agent
    selected_agent = None
    controls: list[float] | None = None

    def research_agent(observation, configuration=None):
        nonlocal selected_agent, controls
        step = int(observation.get("step", 0)) if isinstance(observation, dict) else 0
        if selected_agent is None and step >= DECISION_STEP:
            features = extract_features(observation)
            with torch.no_grad():
                game = torch.from_numpy(features).to(device=device, dtype=torch.float32).unsqueeze(0)
                probs = _classifier_probs(classifier, classifier_meta, features, device)
                opponent = torch.from_numpy(probs).to(device=device, dtype=torch.float32).unsqueeze(0)
                predicted, _, _ = selector(torch.cat([game, opponent], dim=-1))
            controls = predicted[0].detach().cpu().numpy().astype(np.float32).tolist()
            selected_agent = configured_two_control_agent(controls[0], controls[1], 900000 + seed)
        return (selected_agent or fixed_agent)(observation, configuration)

    return research_agent, lambda: controls


def _run_pair(package_dir: Path, seed: int, selector, classifier, classifier_meta, device, index: int) -> dict[str, Any]:
    import kaggle_environments

    sys.path.insert(0, str(package_dir))
    try:
        candidate = _load(package_dir / "APEX4_PPO_CANDIDATE.py", f"candidate_trace_{seed}_{index}")
        sealed = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"sealed_trace_{seed}_{index}")
    finally:
        if sys.path[0] == str(package_dir):
            sys.path.pop(0)

    research_opponent = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"research_opp_{seed}_{index}")
    research_agent, controls_getter = _research_agent_factory(
        sealed, selector, classifier, classifier_meta, device, seed
    )
    env_research = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_candidate = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    errors: list[str] = []
    try:
        env_research.run([research_agent, research_opponent.agent])
        env_candidate.run([candidate.agent, candidate._sealed.agent])
    except Exception as exc:
        errors.append(repr(exc))

    research_steps = env_research.steps
    candidate_steps = env_candidate.steps
    first: dict[str, Any] | None = None
    limit = min(len(research_steps), len(candidate_steps))
    for step in range(DECISION_STEP, limit):
        for player in (0, 1):
            left = _entry_signature(research_steps[step][player])
            right = _entry_signature(candidate_steps[step][player])
            if left != right:
                first = {
                    "step": step,
                    "player": player,
                    "research": left,
                    "candidate": right,
                    "same_action": _stable(left["action"]) == _stable(right["action"]),
                    "same_observation": left["observation_json"] == right["observation_json"],
                }
                break
        if first is not None:
            break

    return {
        "seed": seed,
        "research_steps": len(research_steps),
        "candidate_steps": len(candidate_steps),
        "controls": controls_getter(),
        "first_divergence": first,
        "research_terminal": research_steps[-1] if research_steps else None,
        "candidate_terminal": candidate_steps[-1] if candidate_steps else None,
        "errors": errors,
    }


def run(package_zip: Path, checkpoint: Path, output: Path, seed_start: int, episodes: int) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this audit")
    device = torch.device("cuda:0")
    classifier, classifier_meta = _load_classifier(DEFAULT_CLASSIFIER, device)
    selector = TwoControlSelector().to(device)
    checkpoint_data = torch.load(checkpoint, map_location=device, weights_only=False)
    selector.load_state_dict(checkpoint_data["model_state_dict"])
    selector.eval()

    with tempfile.TemporaryDirectory(prefix="apex4_trajectory_audit_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(package_zip) as archive:
            archive.extractall(package_dir)
        rows = [
            _run_pair(package_dir, seed_start + index, selector, classifier, classifier_meta, device, index)
            for index in range(episodes)
        ]

    divergences = [row["first_divergence"] for row in rows if row["first_divergence"] is not None]
    report = {
        "status": "PASS" if not divergences and not any(row["errors"] for row in rows) else "DIVERGENCE_FOUND",
        "evaluation": "research PPO adapter versus packaged candidate full trajectory audit",
        "package": str(package_zip),
        "checkpoint": str(checkpoint),
        "seed_start": seed_start,
        "episodes": episodes,
        "comparison_start_step": DECISION_STEP,
        "cuda_device": str(device),
        "completed_pairs": sum(row["research_steps"] == 720 and row["candidate_steps"] == 720 for row in rows),
        "divergence_count": len(divergences),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=77000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.package, args.checkpoint, args.output, args.seed_start, args.episodes), indent=2))


if __name__ == "__main__":
    main()
