"""Compare research and packaged PPO inference on identical Kaggle observations."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import configured_two_control_agent
from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(value):
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def run(package_zip: Path, checkpoint: Path, classifier_path: Path, seeds: list[int], output: Path) -> dict:
    import kaggle_environments

    device = torch.device("cuda:0")
    selector = TwoControlSelector().to(device)
    selector.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=False)["model_state_dict"])
    selector.eval()
    classifier = OpponentClassifier().to(device)
    classifier_payload = torch.load(classifier_path, map_location=device, weights_only=False)
    classifier.load_state_dict(classifier_payload["model_state_dict"])
    classifier.eval()
    feature_mean = torch.tensor(classifier_payload["feature_mean"], dtype=torch.float32, device=device)
    feature_std = torch.tensor(classifier_payload["feature_std"], dtype=torch.float32, device=device)

    with tempfile.TemporaryDirectory(prefix="candidate_equivalence_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(package_zip) as archive:
            archive.extractall(package_dir)
        sys.path.insert(0, str(package_dir))
        try:
            candidate = _load(package_dir / "APEX4_PPO_CANDIDATE.py", "candidate_equivalence")
        finally:
            if sys.path[0] == str(package_dir):
                sys.path.pop(0)

        rows = []
        for seed in seeds:
            sealed_ns = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"sealed_obs_{seed}")
            noop = lambda obs: {"farmer": ["PASS"], "hands": [], "market": []}
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            env.run([sealed_ns.agent, noop])
            observation = env.steps[120][0]["observation"]
            features = extract_features(observation)
            opponent = torch.from_numpy(features[60:84]).to(device=device, dtype=torch.float32)
            with torch.inference_mode():
                probs_t = torch.softmax(classifier(((opponent - feature_mean) / feature_std).unsqueeze(0)), dim=-1)
                x = torch.from_numpy(np.concatenate([features, probs_t[0].detach().cpu().numpy()]).astype(np.float32)).to(device).unsqueeze(0)
                controls_t, confidence_t, value_t = selector(x)
            torch_controls = controls_t[0].detach().cpu().numpy().astype(np.float32)
            numpy_result = candidate.predict(features)
            candidate._select_agent(observation, 120)
            candidate_action = candidate._selected_agent(observation, None)
            research_agent = configured_two_control_agent(float(torch_controls[0]), float(torch_controls[1]), 500000 + seed)
            research_action = research_agent(observation, None)
            rows.append({
                "seed": seed,
                "feature_finite": bool(np.isfinite(features).all()),
                "max_probability_error": float(np.max(np.abs(probs_t[0].detach().cpu().numpy() - numpy_result["opponent_probabilities"]))),
                "max_control_error": float(np.max(np.abs(torch_controls - numpy_result["controls"]))),
                "confidence_error": abs(float(confidence_t[0, 0].detach().cpu()) - float(numpy_result["confidence"])),
                "value_error": abs(float(value_t[0, 0].detach().cpu()) - float(numpy_result["value"])),
                "controls": torch_controls.tolist(),
                "candidate_action_equals_research_action": _json(candidate_action) == _json(research_action),
                "candidate_action": candidate_action,
                "research_action": research_action,
            })

    report = {
        "status": "PASS" if all(row["candidate_action_equals_research_action"] for row in rows) else "FAIL",
        "seeds": seeds,
        "decision_step": 120,
        "max_model_error": max(max(row["max_probability_error"] for row in rows), max(row["max_control_error"] for row in rows), max(row["confidence_error"] for row in rows), max(row["value_error"] for row in rows)),
        "all_actions_equal": all(row["candidate_action_equals_research_action"] for row in rows),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=77000)
    parser.add_argument("--seed-count", type=int, default=32)
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    print(json.dumps(run(args.package, args.checkpoint, args.classifier, seeds, args.output), indent=2))


if __name__ == "__main__":
    main()
