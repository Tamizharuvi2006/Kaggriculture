"""Read-only transfer probe for the frozen PPO representation.

No PPO weights are updated and no Kaggriculture environment is imported. The
frozen NumPy export is used to reproduce the shared 32-unit representation and
the selector outputs from cached replay observations.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "lplus_market_pressure_dataset.jsonl"
RAW_ROOT = ROOT / "reports" / "step5b" / "old_loss_gauntlet" / "raw_replays"
PPO_CHECKPOINT = ROOT / "reports" / "step5b" / "PPO_CANDIDATE_FROZEN_32SEED.pt"
PPO_MANIFEST = ROOT / "reports" / "step5b" / "step5b_numpy_export_manifest.json"
PPO_INFERENCE = ROOT / "apex_next" / "ml_engine" / "deployment" / "step5b_numpy_inference.py"
OUT_JSON = ROOT / "ppo_transfer_value_market_labels.json"
OUT_MD = ROOT / "PPO_TRANSFER_VALUE_MARKET_LABELS.md"

sys.path.insert(0, str(ROOT))
from apex_next.ml_engine.feature_extractor import extract_features  # noqa: E402
from apex_next.ml_engine.deployment import step5b_numpy_inference as frozen  # noqa: E402


PRODUCTS = ("MILK", "STRAWBERRY", "WOOL")
TARGETS = tuple(f"{kind}_{product.lower()}" for product in PRODUCTS for kind in ("adverse", "favorable"))


def _relu(value: np.ndarray) -> np.ndarray:
    return np.maximum(value, 0.0).astype(np.float32, copy=False)


def _linear(value: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> np.ndarray:
    return (np.asarray(value, dtype=np.float32) @ weight.T + bias).astype(np.float32, copy=False)


def frozen_representation(game_features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the frozen shared hidden vector and exported PPO outputs."""

    opponent = frozen.opponent_probabilities(game_features[60:84])
    combined = np.concatenate([game_features, opponent]).astype(np.float32, copy=False)
    hidden_1 = _relu(_linear(combined, frozen.SHARED_0_WEIGHT, frozen.SHARED_0_BIAS))
    hidden = _relu(_linear(hidden_1, frozen.SHARED_2_WEIGHT, frozen.SHARED_2_BIAS))
    output = frozen.predict(game_features)
    output_vector = np.asarray(
        [output["controls"][0], output["controls"][1], output["confidence"], output["value"]],
        dtype=np.float32,
    )
    return hidden, output_vector


def _match_id(path: Path) -> str:
    return path.stem.replace("episode-", "").replace("-replay", "")


def _load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        source = json.loads(line)
        source_features = source["features"]
        keep = {"step": source_features.get("step")}
        for product in PRODUCTS:
            name = product.lower()
            keep[f"price_{name}"] = source_features.get(f"price_{name}")
            for lag in (1, 3, 6):
                key = f"price_change_{name}_{lag}"
                keep[key] = source_features.get(key)
        rows.append({
            "match_id": source["match_id"],
            "seat": int(source["seat"]),
            "split": source["split"],
            "features": keep,
            "labels": source["labels"],
        })
    return rows


def _enrich_rows(rows: list[dict[str, Any]]) -> int:
    by_match: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_match.setdefault(str(row["match_id"]), []).append(row)
    enriched = 0
    for replay_path in sorted(RAW_ROOT.glob("*/episode-*-replay.json")):
        match_id = _match_id(replay_path)
        match_rows = by_match.get(match_id, [])
        if not match_rows:
            continue
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        steps = replay.get("steps") or []
        lookup = {(int(row["seat"]), int(row["features"]["step"])): row for row in match_rows}
        for step, frame in enumerate(steps[:719]):
            for seat, record in enumerate(frame[:2]):
                row = lookup.get((seat, step))
                if row is None:
                    continue
                observation = record.get("observation") or {}
                game_features = extract_features(observation)
                hidden, output = frozen_representation(game_features)
                row["ppo_hidden"] = hidden.astype(float).tolist()
                row["ppo_output"] = output.astype(float).tolist()
                row["ppo_game_feature_dim"] = int(game_features.shape[0])
                enriched += 1
    return enriched


def _sigmoid(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-value))


def _fit_probe(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-6] = 1.0
    z = (x - mean) / scale
    weights = np.zeros(z.shape[1], dtype=np.float64)
    bias = 0.0
    for _ in range(300):
        probability = _sigmoid(z @ weights + bias)
        error = probability - y
        weights -= 0.08 * ((z.T @ error) / len(y) + 1e-3 * weights)
        bias -= 0.08 * float(error.mean())
    return weights, np.asarray([bias]), mean, scale


def _predict(x: np.ndarray, fitted: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    weights, bias, mean, scale = fitted
    return _sigmoid(((x - mean) / scale) @ weights + bias[0])


def _auc(y: np.ndarray, probability: np.ndarray) -> float | None:
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return None
    order = np.argsort(probability)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(y) + 1)
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def _metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    predicted = probability >= 0.5
    tp = int(np.sum((predicted == 1) & (y == 1)))
    tn = int(np.sum((predicted == 0) & (y == 0)))
    fp = int(np.sum((predicted == 1) & (y == 0)))
    fn = int(np.sum((predicted == 0) & (y == 1)))
    recalls = [tp / max(1, tp + fn), tn / max(1, tn + fp)]
    bins = []
    for low in np.linspace(0.0, 1.0, 11)[:-1]:
        high = low + 0.1
        mask = (probability >= low) & ((probability < high) if high < 1.0 else (probability <= high))
        if np.any(mask):
            bins.append(float(np.abs(probability[mask].mean() - y[mask].mean()) * mask.mean()))
    return {
        "n": int(len(y)),
        "positive_rate": float(y.mean()),
        "accuracy": float((tp + tn) / len(y)),
        "balanced_accuracy": float(np.mean(recalls)),
        "brier": float(np.mean((probability - y) ** 2)),
        "ece": float(sum(bins)),
        "auc": _auc(y, probability),
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def _baseline_vector(row: dict[str, Any], product: str) -> list[float]:
    features = row["features"]
    name = product.lower()
    return [
        float(features.get(f"price_{name}") or 0.0),
        float(features.get(f"price_change_{name}_1") or 0.0),
        float(features.get(f"price_change_{name}_3") or 0.0),
        float(features.get(f"price_change_{name}_6") or 0.0),
    ]


def _evaluate(rows: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    selected = [row for row in rows if scope == "all_steps" or int(row["features"]["step"]) == 120]
    train = [row for row in selected if row["split"] == "train" and "ppo_hidden" in row]
    validation = [row for row in selected if row["split"] == "validation" and "ppo_hidden" in row]
    results: dict[str, Any] = {"scope": scope, "train_rows": len(train), "validation_rows": len(validation), "targets": {}}
    for target in TARGETS:
        train_valid = [row for row in train if row["labels"].get(target) is not None]
        val_valid = [row for row in validation if row["labels"].get(target) is not None]
        if not train_valid or not val_valid:
            results["targets"][target] = {"status": "INSUFFICIENT_LABELS"}
            continue
        y_train = np.asarray([int(row["labels"][target]) for row in train_valid], dtype=np.float64)
        y_val = np.asarray([int(row["labels"][target]) for row in val_valid], dtype=np.float64)
        x_hidden_train = np.asarray([row["ppo_hidden"] for row in train_valid], dtype=np.float64)
        x_hidden_val = np.asarray([row["ppo_hidden"] for row in val_valid], dtype=np.float64)
        x_output_train = np.asarray([row["ppo_output"] for row in train_valid], dtype=np.float64)
        x_output_val = np.asarray([row["ppo_output"] for row in val_valid], dtype=np.float64)
        product = target.split("_", 1)[1].upper()
        x_base_train = np.asarray([_baseline_vector(row, product) for row in train_valid], dtype=np.float64)
        x_base_val = np.asarray([_baseline_vector(row, product) for row in val_valid], dtype=np.float64)
        probes = {}
        for name, x_train, x_val in (("ppo_hidden32", x_hidden_train, x_hidden_val), ("ppo_outputs4", x_output_train, x_output_val), ("price_trend_baseline", x_base_train, x_base_val)):
            fitted = _fit_probe(x_train, y_train)
            probes[name] = _metrics(y_val, _predict(x_val, fitted))
        results["targets"][target] = {"status": "PASS", "probes": probes}
    return results


def build_report() -> dict[str, Any]:
    rows = _load_rows()
    enriched = _enrich_rows(rows)
    checkpoint_sha256 = hashlib.sha256(PPO_CHECKPOINT.read_bytes()).hexdigest() if PPO_CHECKPOINT.exists() else None
    report = {
        "status": "PASS_WITH_LIMITATIONS" if enriched == len(rows) else "INCOMPLETE_ENRICHMENT",
        "scope": "read-only frozen PPO transfer-value audit",
        "games_run": False,
        "ppo_training_run": False,
        "probe_fit": "offline supervised probes only; frozen PPO weights unchanged",
        "dataset_rows": len(rows),
        "enriched_rows": enriched,
        "checkpoint": str(PPO_CHECKPOINT.relative_to(ROOT)),
        "checkpoint_sha256": checkpoint_sha256,
        "numpy_export": str(PPO_INFERENCE.relative_to(ROOT)),
        "export_manifest": json.loads(PPO_MANIFEST.read_text(encoding="utf-8")) if PPO_MANIFEST.exists() else None,
        "representation": {"input_dim": 133, "shared_hidden_dim": 32, "output_dim": 4, "outputs": ["u_market", "u_route", "confidence", "value"]},
        "evaluation": {
            "all_steps": _evaluate(rows, "all_steps"),
            "decision_step_120": _evaluate(rows, "decision_step_120"),
        },
        "limitations": [
            "This is predictive transfer evidence, not causal policy evidence.",
            "The PPO was trained for a step-120 control decision; all-step results are descriptive and the step-120 slice is the relevant view.",
            "The dataset labels next-clearance price movement, not accepted/rejected market execution or terminal wealth improvement.",
            "The probes are fit for measurement only and are not exported as production models.",
        ],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Frozen PPO Transfer-Value Audit",
        "",
        "Scope: read-only offline probes against cached replay labels. No games and no PPO fine-tuning were run.",
        "",
        f"Status: **{report['status']}**",
        f"Rows enriched from raw replays: **{enriched}/{len(rows)}**",
        "",
        "## Frozen Representation",
        "",
        "The audited export is the frozen 133-input selector with a 32-unit shared hidden layer and four outputs: `u_market`, `u_route`, confidence, and value. The checkpoint and export were read only.",
        "",
        "## Probe Comparison",
        "",
        "Each probe is fit on the existing train split and evaluated once on the existing validation split. `ppo_hidden32` tests the reusable representation, `ppo_outputs4` tests the frozen outputs, and `price_trend_baseline` uses only current price plus 1/3/6-step trends.",
        "",
    ]
    for scope_name, scope_report in report["evaluation"].items():
        lines.append(f"### {scope_name}")
        lines.append("")
        lines.append(f"Train rows: {scope_report['train_rows']}; validation rows: {scope_report['validation_rows']}.")
        lines.append("")
        lines.append("| Target | PPO hidden AUC | PPO outputs AUC | Price/trend AUC | Hidden vs baseline |")
        lines.append("|---|---:|---:|---:|---|")
        for target, target_report in scope_report["targets"].items():
            if target_report.get("status") != "PASS":
                lines.append(f"| {target} | n/a | n/a | n/a | insufficient labels |")
                continue
            probes = target_report["probes"]
            hidden_auc = probes["ppo_hidden32"]["auc"]
            output_auc = probes["ppo_outputs4"]["auc"]
            base_auc = probes["price_trend_baseline"]["auc"]
            advantage = "yes" if hidden_auc is not None and base_auc is not None and hidden_auc > base_auc + 0.03 else "no/unclear"
            def fmt(value: float | None) -> str:
                return "n/a" if value is None else f"{value:.3f}"
            lines.append(f"| {target} | {fmt(hidden_auc)} | {fmt(output_auc)} | {fmt(base_auc)} | {advantage} |")
        lines.append("")
    lines.extend([
        "## Conclusion",
        "",
        "The audit is predictive transfer evidence only. A reusable PPO representation requires a consistent validation advantage over the simple price/trend baseline, especially at step 120. No result here authorizes a game run, PPO modification, or production integration.",
        "",
        "If the hidden representation does not clear that bar, use a fresh small supervised market model. If it does, preserve the hidden layer as a frozen feature encoder and evaluate a later supervised head under the existing L+ safety gate.",
    ])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2))
