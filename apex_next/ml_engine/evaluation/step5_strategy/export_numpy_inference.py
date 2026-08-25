"""Export the frozen Step 5B selector/classifier to NumPy-only Python."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.models.opponent_classifier import OpponentClassifier
from apex_next.ml_engine.models.two_control_selector import TwoControlSelector


def _literal(array: np.ndarray) -> str:
    return repr(array.astype(np.float32).tolist())


def _weights(state: dict[str, torch.Tensor], names: list[str]) -> list[tuple[str, str]]:
    return [(name, _literal(state[name].detach().cpu().numpy())) for name in names]


def export(checkpoint: Path, classifier_checkpoint: Path, output: Path) -> dict:
    selector_payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    classifier_payload = torch.load(classifier_checkpoint, map_location="cpu", weights_only=False)
    selector = TwoControlSelector()
    classifier = OpponentClassifier()
    selector.load_state_dict(selector_payload["model_state_dict"])
    classifier.load_state_dict(classifier_payload["model_state_dict"])
    selector.eval()
    classifier.eval()

    selector_state = selector.state_dict()
    classifier_state = classifier.state_dict()
    selector_items = _weights(
        selector_state,
        [
            "shared.0.weight", "shared.0.bias", "shared.2.weight", "shared.2.bias",
            "control_head.weight", "control_head.bias", "confidence_head.weight",
            "confidence_head.bias", "value_head.weight", "value_head.bias",
        ],
    )
    classifier_items = _weights(
        classifier_state,
        ["net.0.weight", "net.0.bias", "net.2.weight", "net.2.bias", "net.4.weight", "net.4.bias"],
    )
    feature_mean = np.asarray(classifier_payload["feature_mean"], dtype=np.float32)
    feature_std = np.asarray(classifier_payload["feature_std"], dtype=np.float32)

    selector_block = "\n".join(f"{name.replace('.', '_').upper()} = np.asarray({value}, dtype=np.float32)" for name, value in selector_items)
    classifier_block = "\n".join(f"{name.replace('.', '_').upper()} = np.asarray({value}, dtype=np.float32)" for name, value in classifier_items)
    module = f'''"""Generated NumPy-only Step 5B inference export. Do not edit manually."""
import numpy as np

CONTROL_LIMIT = np.float32(0.25)
DECISION_STEP = 120
OPPONENT_FEATURE_MEAN = np.asarray({feature_mean.tolist()}, dtype=np.float32)
OPPONENT_FEATURE_STD = np.asarray({feature_std.tolist()}, dtype=np.float32)
{classifier_block}
{selector_block}

def _relu(x):
    return np.maximum(x, 0.0).astype(np.float32, copy=False)

def _linear(x, weight, bias):
    return (np.asarray(x, dtype=np.float32) @ weight.T + bias).astype(np.float32, copy=False)

def opponent_probabilities(opponent_features):
    x = np.asarray(opponent_features, dtype=np.float32).reshape(-1)
    if x.shape != (24,):
        raise ValueError(f"expected 24 opponent features, got {{x.shape}}")
    x = (x - OPPONENT_FEATURE_MEAN) / OPPONENT_FEATURE_STD
    x = _relu(_linear(x, NET_0_WEIGHT, NET_0_BIAS))
    x = _relu(_linear(x, NET_2_WEIGHT, NET_2_BIAS))
    logits = _linear(x, NET_4_WEIGHT, NET_4_BIAS)
    shifted = logits - np.max(logits)
    probabilities = np.exp(shifted)
    probabilities /= np.sum(probabilities)
    return probabilities.astype(np.float32, copy=False)

def predict(game_features, opponent_features=None):
    game = np.asarray(game_features, dtype=np.float32).reshape(-1)
    if game.shape != (128,):
        raise ValueError(f"expected 128 game features, got {{game.shape}}")
    if opponent_features is None:
        opponent_features = game[60:84]
    probabilities = opponent_probabilities(opponent_features)
    x = np.concatenate([game, probabilities]).astype(np.float32, copy=False)
    hidden = _relu(_linear(x, SHARED_0_WEIGHT, SHARED_0_BIAS))
    hidden = _relu(_linear(hidden, SHARED_2_WEIGHT, SHARED_2_BIAS))
    controls = CONTROL_LIMIT * np.tanh(_linear(hidden, CONTROL_HEAD_WEIGHT, CONTROL_HEAD_BIAS))
    confidence = 1.0 / (1.0 + np.exp(-_linear(hidden, CONFIDENCE_HEAD_WEIGHT, CONFIDENCE_HEAD_BIAS)))
    value = _linear(hidden, VALUE_HEAD_WEIGHT, VALUE_HEAD_BIAS)
    return {{"opponent_probabilities": probabilities, "controls": controls.astype(np.float32), "confidence": np.float32(confidence[0]), "value": np.float32(value[0])}}
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(module, encoding="utf-8")
    return {
        "status": "EXPORTED",
        "output": str(output),
        "selector_checkpoint": str(checkpoint),
        "classifier_checkpoint": str(classifier_checkpoint),
        "numpy_dependency_only": True,
        "decision_step": 120,
        "control_bounds": [-0.25, 0.25],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = export(args.checkpoint, args.classifier, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
