"""Derive Step 3 opponent archetype labels from real demonstration features.

The labels are intentionally generated from the recorded Step 2 state features.
No synthetic labels or opponent-name shortcuts are used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.feature_extractor import FEATURE_DIM


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CURRENT_DATA_DIR = DATA_DIR / "current" / "step3g_targeted_1000"
DEFAULT_INPUT = CURRENT_DATA_DIR / "expert_demos_step3g_targeted_1000.npz"
DEFAULT_OUTPUT = CURRENT_DATA_DIR / "opponent_labels_step3g_targeted_1000.npz"
DEFAULT_AUDIT = CURRENT_DATA_DIR / "opponent_labels_step3g_targeted_1000_audit.json"

CLASS_NAMES = (
    "LIVESTOCK_HEAVY",
    "CROP_HEAVY",
    "BALANCED",
    "AGGRESSIVE_EXPAND",
    "MARKET_MANIPULATOR",
)

LIVESTOCK_HEAVY = 0
CROP_HEAVY = 1
BALANCED = 2
AGGRESSIVE_EXPAND = 3
MARKET_MANIPULATOR = 4


def label_opponents(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    audit_path: Path = DEFAULT_AUDIT,
) -> dict[str, Any]:
    """Create transition-level and episode-level opponent labels."""

    with np.load(input_path, allow_pickle=False) as data:
        features = data["features"]
        opponent_features = data["opponent_features"]
        terminals = data["terminals"]
        episode_ids = data["episode_ids"]
        steps = data["steps"]
        opponent_ids = data["opponent_ids"] if "opponent_ids" in data.files else None
        market_pattern_available = "opponent_actions_json" in data.files
        opponent_actions_json = data["opponent_actions_json"] if market_pattern_available else None

        _validate_inputs(features, opponent_features, terminals, episode_ids, steps)

        transition_labels = np.full(features.shape[0], -1, dtype=np.int64)
        unique_episode_ids = np.unique(episode_ids)
        episode_labels = np.full(unique_episode_ids.shape[0], -1, dtype=np.int64)
        episode_reasons: list[str] = []
        episode_evidence: list[dict[str, Any]] = []

        for out_index, episode_id in enumerate(unique_episode_ids):
            indices = np.flatnonzero(episode_ids == episode_id)
            label, reason, evidence = _classify_episode(
                features=features,
                opponent_features=opponent_features,
                terminals=terminals,
                steps=steps,
                indices=indices,
                market_pattern_available=market_pattern_available,
                opponent_actions_json=opponent_actions_json,
            )
            transition_labels[indices] = label
            episode_labels[out_index] = label
            episode_reasons.append(reason)
            evidence["episode_id"] = int(episode_id)
            if opponent_ids is not None:
                evidence["opponent_id"] = _row_text(opponent_ids[indices[0]])
            episode_evidence.append(evidence)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        labels=transition_labels,
        transition_labels=transition_labels,
        episode_labels=episode_labels,
        episode_ids=unique_episode_ids.astype(np.int32, copy=False),
        class_names=np.asarray([name.encode("utf-8") for name in CLASS_NAMES], dtype=np.bytes_),
        label_reasons=np.asarray([reason.encode("utf-8") for reason in episode_reasons], dtype=np.bytes_),
        source_dataset=np.asarray(str(input_path).encode("utf-8"), dtype=np.bytes_),
    )

    validation = validate_labels(output_path, expected_transitions=int(features.shape[0]), expected_episodes=len(unique_episode_ids))
    audit = _build_audit(
        input_path=input_path,
        output_path=output_path,
        transition_labels=transition_labels,
        episode_labels=episode_labels,
        validation=validation,
        episode_evidence=episode_evidence,
        market_pattern_available=market_pattern_available,
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def validate_labels(path: Path, expected_transitions: int | None = None, expected_episodes: int | None = None) -> dict[str, Any]:
    """Reload Step 3 labels without pickle and verify the classifier contract."""

    with np.load(path, allow_pickle=False) as data:
        labels = data["labels"]
        transition_labels = data["transition_labels"]
        episode_labels = data["episode_labels"]
        episode_ids = data["episode_ids"]
        class_names = data["class_names"]
        label_reasons = data["label_reasons"]

        checks = {
            "labels_shape": labels.ndim == 1,
            "labels_dtype": labels.dtype == np.int64,
            "labels_alias_matches": np.array_equal(labels, transition_labels),
            "labels_valid_range": bool(((labels >= 0) & (labels < len(CLASS_NAMES))).all()),
            "unlabeled_zero": int((labels < 0).sum()) == 0,
            "episode_labels_shape": episode_labels.shape == episode_ids.shape,
            "episode_labels_dtype": episode_labels.dtype == np.int64,
            "episode_labels_valid_range": bool(((episode_labels >= 0) & (episode_labels < len(CLASS_NAMES))).all()),
            "class_names_reloadable": tuple(_row_text(row) for row in class_names) == CLASS_NAMES,
            "label_reasons_count": label_reasons.shape == episode_labels.shape,
        }
        if expected_transitions is not None:
            checks["transition_count_matches_expected"] = labels.shape == (expected_transitions,)
        if expected_episodes is not None:
            checks["episode_count_matches_expected"] = episode_labels.shape == (expected_episodes,)

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "transition_count": int(labels.shape[0]),
        "episode_count": int(episode_labels.shape[0]),
        "checks": checks,
    }


def _classify_episode(
    features: np.ndarray,
    opponent_features: np.ndarray,
    terminals: np.ndarray,
    steps: np.ndarray,
    indices: np.ndarray,
    market_pattern_available: bool,
    opponent_actions_json: np.ndarray | None = None,
) -> tuple[int, str, dict[str, Any]]:
    terminal_indices = indices[terminals[indices]]
    final_index = int(terminal_indices[-1] if terminal_indices.size else indices[-1])
    final_opp = opponent_features[final_index]

    final_livestock = float(final_opp[4] * 14.0)
    final_strawberry_tiles = float(final_opp[8] * 34.0)
    max_strawberry_tiles = float((opponent_features[indices, 8] * 34.0).max())
    final_opp_quadrants = float(final_opp[1] * 4.0)
    final_own_quadrants = float(features[final_index, 6] * 4.0)

    step_200_indices = indices[steps[indices] == 200]
    if step_200_indices.size:
        step_200_index = int(step_200_indices[-1])
        expanded_at_step_200 = bool(opponent_features[step_200_index, 23] > 0.5)
        step_200_opp_quadrants = float(opponent_features[step_200_index, 1] * 4.0)
        step_200_own_quadrants = float(features[step_200_index, 6] * 4.0)
    else:
        expanded_at_step_200 = False
        step_200_opp_quadrants = None
        step_200_own_quadrants = None

    market_stats = _market_stats(opponent_actions_json, indices) if opponent_actions_json is not None else {}
    market_manipulator = _is_market_manipulator(market_stats)

    if market_manipulator:
        return MARKET_MANIPULATOR, "conservative_market_churn", _evidence(
            final_livestock,
            final_strawberry_tiles,
            max_strawberry_tiles,
            final_opp_quadrants,
            final_own_quadrants,
            expanded_at_step_200,
            step_200_opp_quadrants,
            step_200_own_quadrants,
            market_pattern_available,
            market_stats,
        )
    if max_strawberry_tiles > 20.0 and market_stats.get("buy_seed_strawberry_orders", 0) >= 100:
        return CROP_HEAVY, "max_strawberry_tiles_gt_20_and_strawberry_seed_orders_ge_100", _evidence(
            final_livestock,
            final_strawberry_tiles,
            max_strawberry_tiles,
            final_opp_quadrants,
            final_own_quadrants,
            expanded_at_step_200,
            step_200_opp_quadrants,
            step_200_own_quadrants,
            market_pattern_available,
            market_stats,
        )
    if expanded_at_step_200:
        return AGGRESSIVE_EXPAND, "opponent_land_gt_own_at_step_200", _evidence(
            final_livestock,
            final_strawberry_tiles,
            max_strawberry_tiles,
            final_opp_quadrants,
            final_own_quadrants,
            expanded_at_step_200,
            step_200_opp_quadrants,
            step_200_own_quadrants,
            market_pattern_available,
            market_stats,
        )
    if final_livestock > 8.0:
        return LIVESTOCK_HEAVY, "final_livestock_gt_8", _evidence(
            final_livestock,
            final_strawberry_tiles,
            max_strawberry_tiles,
            final_opp_quadrants,
            final_own_quadrants,
            expanded_at_step_200,
            step_200_opp_quadrants,
            step_200_own_quadrants,
            market_pattern_available,
            market_stats,
        )
    return BALANCED, "default_balanced", _evidence(
        final_livestock,
        final_strawberry_tiles,
        max_strawberry_tiles,
        final_opp_quadrants,
        final_own_quadrants,
        expanded_at_step_200,
        step_200_opp_quadrants,
        step_200_own_quadrants,
        market_pattern_available,
        market_stats,
    )


def _evidence(
    final_livestock: float,
    final_strawberry_tiles: float,
    max_strawberry_tiles: float,
    final_opp_quadrants: float,
    final_own_quadrants: float,
    expanded_at_step_200: bool,
    step_200_opp_quadrants: float | None,
    step_200_own_quadrants: float | None,
    market_pattern_available: bool,
    market_stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "final_livestock_count": round(final_livestock, 6),
        "final_strawberry_tiles": round(final_strawberry_tiles, 6),
        "max_strawberry_tiles": round(max_strawberry_tiles, 6),
        "final_opponent_quadrants": round(final_opp_quadrants, 6),
        "final_own_quadrants": round(final_own_quadrants, 6),
        "expanded_at_step_200": expanded_at_step_200,
        "step_200_opponent_quadrants": None if step_200_opp_quadrants is None else round(step_200_opp_quadrants, 6),
        "step_200_own_quadrants": None if step_200_own_quadrants is None else round(step_200_own_quadrants, 6),
        "market_pattern_available": market_pattern_available,
        "market_stats": market_stats or {},
    }


def _market_stats(opponent_actions_json: np.ndarray, indices: np.ndarray) -> dict[str, int]:
    stats = {
        "market_orders": 0,
        "sell_orders": 0,
        "buy_product_orders": 0,
        "buy_product_wheat_orders": 0,
        "buy_seed_strawberry_orders": 0,
        "sell_wheat_orders": 0,
    }
    for index in indices:
        try:
            action = json.loads(_row_text(opponent_actions_json[int(index)]))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for order in action.get("market", []):
            if not isinstance(order, list) or not order:
                continue
            command = str(order[0])
            product = str(order[1]) if len(order) > 1 else ""
            stats["market_orders"] += 1
            if command == "SELL":
                stats["sell_orders"] += 1
                if product == "WHEAT":
                    stats["sell_wheat_orders"] += 1
            if command == "BUY_PRODUCT":
                stats["buy_product_orders"] += 1
                if product == "WHEAT":
                    stats["buy_product_wheat_orders"] += 1
            if command == "BUY_SEED" and product == "STRAWBERRY":
                stats["buy_seed_strawberry_orders"] += 1
    return stats


def _is_market_manipulator(market_stats: dict[str, int]) -> bool:
    return (
        market_stats.get("buy_product_wheat_orders", 0) >= 1000
        and market_stats.get("sell_wheat_orders", 0) >= 500
        and market_stats.get("buy_product_orders", 0) + market_stats.get("sell_orders", 0) >= 3000
    )


def _build_audit(
    input_path: Path,
    output_path: Path,
    transition_labels: np.ndarray,
    episode_labels: np.ndarray,
    validation: dict[str, Any],
    episode_evidence: list[dict[str, Any]],
    market_pattern_available: bool,
) -> dict[str, Any]:
    transition_distribution = _distribution(transition_labels)
    episode_distribution = _distribution(episode_labels)
    max_transition_ratio = max((item["ratio"] for item in transition_distribution.values()), default=0.0)
    zero_transition_classes = [name for name, item in transition_distribution.items() if item["count"] == 0]
    warnings = []
    if zero_transition_classes:
        warnings.append(f"zero_count_classes={','.join(zero_transition_classes)}")
    if max_transition_ratio >= 0.80:
        warnings.append(f"severe_transition_imbalance_max_ratio={max_transition_ratio:.6f}")
    if market_pattern_available:
        warnings.append("market_manipulator_rule_applied_from_opponent_action_telemetry")
    else:
        warnings.append("market_manipulator_rule_not_applied_opponent_sell_patterns_not_recorded_in_dataset")

    return {
        "status": "PASS" if validation["status"] == "PASS" else "FAIL",
        "source_dataset": str(input_path),
        "output_path": str(output_path),
        "total_transitions": int(transition_labels.shape[0]),
        "total_episodes": int(episode_labels.shape[0]),
        "class_mapping": {str(index): name for index, name in enumerate(CLASS_NAMES)},
        "transition_class_distribution": transition_distribution,
        "episode_class_distribution": episode_distribution,
        "unlabeled": int((transition_labels < 0).sum()),
        "invalid_labels": int(((transition_labels < 0) | (transition_labels >= len(CLASS_NAMES))).sum()),
        "severely_imbalanced": bool(zero_transition_classes or max_transition_ratio >= 0.80),
        "warnings": warnings,
        "validation": validation,
        "rules": {
            "livestock_heavy": "final COW+SHEEP > 8",
            "crop_heavy": "max STRAWBERRY tiles > 20 and BUY_SEED:STRAWBERRY >= 100",
            "aggressive_expand": "opponent land > own land at step 200",
            "market_manipulator": "BUY_PRODUCT:WHEAT >= 1000, SELL:WHEAT >= 500, and BUY_PRODUCT+SELL >= 3000"
            if market_pattern_available
            else "requires opponent sell-pattern telemetry, unavailable in dataset",
            "balanced": "fallback when no other rule fires",
        },
        "sample_episode_evidence": episode_evidence[:20],
    }


def _distribution(labels: np.ndarray) -> dict[str, dict[str, float | int]]:
    total = max(int(labels.shape[0]), 1)
    return {
        name: {
            "count": int((labels == index).sum()),
            "ratio": round(float((labels == index).sum()) / total, 6),
        }
        for index, name in enumerate(CLASS_NAMES)
    }


def _validate_inputs(
    features: np.ndarray,
    opponent_features: np.ndarray,
    terminals: np.ndarray,
    episode_ids: np.ndarray,
    steps: np.ndarray,
) -> None:
    transition_count = int(features.shape[0])
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        raise AssertionError(f"expected features shape (N, {FEATURE_DIM}), got {features.shape}")
    if features.dtype != np.float32:
        raise AssertionError(f"expected features dtype float32, got {features.dtype}")
    if opponent_features.shape != (transition_count, 24):
        raise AssertionError(f"expected opponent_features shape ({transition_count}, 24), got {opponent_features.shape}")
    if opponent_features.dtype != np.float32:
        raise AssertionError(f"expected opponent_features dtype float32, got {opponent_features.dtype}")
    if not np.allclose(opponent_features, features[:, 60:84]):
        raise AssertionError("opponent_features does not match features[:, 60:84]")
    if not np.isfinite(features).all() or not np.isfinite(opponent_features).all():
        raise AssertionError("features contain NaN or Inf")
    if terminals.shape != (transition_count,) or terminals.dtype != np.bool_:
        raise AssertionError("invalid terminals shape or dtype")
    if episode_ids.shape != (transition_count,) or episode_ids.dtype != np.int32:
        raise AssertionError("invalid episode_ids shape or dtype")
    if steps.shape != (transition_count,) or steps.dtype != np.int16:
        raise AssertionError("invalid steps shape or dtype")
    if int(terminals.sum()) != len(np.unique(episode_ids)):
        raise AssertionError("terminal count does not match episode count")


def _row_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Label Step 2 opponent archetypes.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    audit = label_opponents(input_path=args.input, output_path=args.output, audit_path=args.audit)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
