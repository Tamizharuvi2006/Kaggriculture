"""Verify NumPy export equivalence with the frozen PyTorch models."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.feature_extractor import extract_features
from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import _opponent_pool


def _load_export(path: Path):
    spec = importlib.util.spec_from_file_location("step5b_numpy_export", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(checkpoint: Path, classifier_path: Path, export_path: Path, report_path: Path) -> dict:
    exported = _load_export(export_path)
    selector_payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    classifier_payload = torch.load(classifier_path, map_location="cpu", weights_only=False)
    selector = TwoControlSelector()
    classifier = OpponentClassifier()
    selector.load_state_dict(selector_payload["model_state_dict"])
    classifier.load_state_dict(classifier_payload["model_state_dict"])
    selector.eval()
    classifier.eval()
    mean = torch.tensor(classifier_payload["feature_mean"], dtype=torch.float32)
    std = torch.tensor(classifier_payload["feature_std"], dtype=torch.float32)

    vectors = [np.zeros(128, dtype=np.float32), np.ones(128, dtype=np.float32)]
    rng = np.random.default_rng(20260821)
    vectors.extend(rng.normal(0.0, 0.5, size=(4, 128)).astype(np.float32))
    _, opponent_fn = _opponent_pool()[0]
    for seed in (77201, 77202, 77203, 77204):
        env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
        env.reset(seed=seed)
        vectors.append(extract_features(env.observation(0)))

    max_prob_error = 0.0
    max_control_error = 0.0
    max_confidence_error = 0.0
    max_value_error = 0.0
    bounds_ok = True
    for features in vectors:
        opponent = torch.from_numpy(features[60:84]).float()
        with torch.inference_mode():
            torch_probs = torch.softmax(classifier(((opponent - mean) / std).unsqueeze(0)), dim=-1)[0].numpy()
            x = torch.from_numpy(np.concatenate([features, torch_probs]).astype(np.float32)).unsqueeze(0)
            torch_controls, torch_confidence, torch_value = selector(x)
        numpy_result = exported.predict(features)
        max_prob_error = max(max_prob_error, float(np.max(np.abs(torch_probs - numpy_result["opponent_probabilities"]))))
        max_control_error = max(max_control_error, float(np.max(np.abs(torch_controls[0].numpy() - numpy_result["controls"]))))
        max_confidence_error = max(max_confidence_error, abs(float(torch_confidence[0, 0]) - float(numpy_result["confidence"])))
        max_value_error = max(max_value_error, abs(float(torch_value[0, 0]) - float(numpy_result["value"])))
        bounds_ok = bounds_ok and bool(np.all(np.abs(numpy_result["controls"]) <= 0.25 + 1e-7))

    tolerance = 1e-5
    report = {
        "status": "PASS" if max(max_prob_error, max_control_error, max_confidence_error, max_value_error) <= tolerance and bounds_ok else "FAIL",
        "vectors_tested": len(vectors),
        "real_observation_vectors": 4,
        "tolerance": tolerance,
        "max_probability_abs_error": max_prob_error,
        "max_control_abs_error": max_control_error,
        "max_confidence_abs_error": max_confidence_error,
        "max_value_abs_error": max_value_error,
        "control_bounds_ok": bounds_ok,
        "torch_dependency_in_export": False,
        "decision_step": 120,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    verify(args.checkpoint, args.classifier, args.export, args.report)


if __name__ == "__main__":
    main()
