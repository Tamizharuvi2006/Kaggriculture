"""Diagnose why Step 3 opponent labels lack class diversity.

This script reads the real Step 2 demonstration dataset and reports the
opponent-state distributions that drive the documented archetype rules.
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


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_ENGINE_DIR / "data"
INVALIDATED_DATA_DIR = DATA_DIR / "invalidated" / "original_seat_bug"
DIAGNOSTICS_DIR = ML_ENGINE_DIR / "evaluation" / "step3_diagnostics"
DEFAULT_INPUT = INVALIDATED_DATA_DIR / "expert_demos.npz"
DEFAULT_OUTPUT = DIAGNOSTICS_DIR / "step3b_label_diagnostics.json"
DEFAULT_MARKDOWN = DIAGNOSTICS_DIR / "step3b_label_diagnostics.md"


def diagnose_labels(input_path: Path = DEFAULT_INPUT) -> dict[str, Any]:
    """Return a JSON-serializable diagnostic summary for Step 3B."""

    with np.load(input_path, allow_pickle=False) as data:
        features = data["features"]
        opponent_features = data["opponent_features"]
        episode_ids = data["episode_ids"]
        steps = data["steps"]
        terminals = data["terminals"]
        opponent_ids = data["opponent_ids"] if "opponent_ids" in data.files else None
        data_files = tuple(data.files)

        _validate_dataset(features, opponent_features, episode_ids, steps, terminals)
        terminal_indices = np.flatnonzero(terminals)
        step_200_indices = np.flatnonzero(steps == 200)
        unique_episode_ids = np.unique(episode_ids)

        opp_cows = opponent_features[:, 2] * 14.0
        opp_sheep = opponent_features[:, 3] * 14.0
        opp_livestock = opponent_features[:, 4] * 14.0
        opp_workers = opponent_features[:, 5] * 13.0
        opp_planted_ratio = opponent_features[:, 6]
        opp_mature_ratio = opponent_features[:, 7]
        opp_strawberry = opponent_features[:, 8] * 34.0
        opp_melon = opponent_features[:, 9] * 12.0
        opp_wheat = opponent_features[:, 10] * 10.0
        opp_tomato = opponent_features[:, 11] * 8.0
        opp_carrot = opponent_features[:, 12] * 8.0
        opp_land = opponent_features[:, 1] * 4.0
        own_land = features[:, 6] * 4.0
        land_advantage = opp_land - own_land

        first_expansion_steps = _first_steps_where(episode_ids, steps, opp_land > 1.0)
        first_land_advantage_steps = _first_steps_where(episode_ids, steps, land_advantage > 0.0)

        final_opp = opponent_features[terminal_indices]
        final_features = features[terminal_indices]
        final_livestock = final_opp[:, 4] * 14.0
        final_strawberry = final_opp[:, 8] * 34.0
        final_land = final_opp[:, 1] * 4.0
        final_own_land = final_features[:, 6] * 4.0

        step_200_opp_land = opponent_features[step_200_indices, 1] * 4.0
        step_200_own_land = features[step_200_indices, 6] * 4.0
        step_200_land_advantage = step_200_opp_land - step_200_own_land

        market_telemetry = _market_telemetry(data_files)
        report = {
            "status": "PASS",
            "source_dataset": str(input_path),
            "total_transitions": int(features.shape[0]),
            "total_episodes": int(unique_episode_ids.shape[0]),
            "terminal_count": int(terminals.sum()),
            "step_range": {"min": int(steps.min()), "max": int(steps.max())},
            "dataset_arrays": list(data_files),
            "opponent_pool_transition_counts": _opponent_pool_counts(opponent_ids),
            "feature_contract": {
                "features_shape": list(features.shape),
                "features_dtype": str(features.dtype),
                "opponent_features_shape": list(opponent_features.shape),
                "opponent_features_dtype": str(opponent_features.dtype),
                "opponent_features_match_slice": bool(np.allclose(opponent_features, features[:, 60:84])),
            },
            "rule_thresholds": {
                "livestock_heavy": "final opponent COW+SHEEP > 8",
                "crop_heavy": "final opponent STRAWBERRY tiles > 20",
                "aggressive_expand": "opponent land count > own land count at step 200",
                "market_manipulator": "unusual opponent sell patterns",
            },
            "transition_distributions": {
                "opponent_cows": _stats(opp_cows),
                "opponent_sheep": _stats(opp_sheep),
                "opponent_cows_plus_sheep": _stats(opp_livestock),
                "opponent_strawberry_tiles": _stats(opp_strawberry),
                "opponent_melon_tiles": _stats(opp_melon),
                "opponent_wheat_tiles": _stats(opp_wheat),
                "opponent_tomato_tiles": _stats(opp_tomato),
                "opponent_carrot_tiles": _stats(opp_carrot),
                "opponent_land_count": _stats(opp_land),
                "own_land_count": _stats(own_land),
                "opponent_land_minus_own_land": _stats(land_advantage),
                "opponent_worker_count": _stats(opp_workers),
                "opponent_planted_tile_ratio": _stats(opp_planted_ratio),
                "opponent_mature_tile_ratio": _stats(opp_mature_ratio),
            },
            "terminal_distributions": {
                "final_opponent_cows_plus_sheep": _stats(final_livestock),
                "final_opponent_strawberry_tiles": _stats(final_strawberry),
                "final_opponent_land_count": _stats(final_land),
                "final_own_land_count": _stats(final_own_land),
                "final_opponent_land_minus_own_land": _stats(final_land - final_own_land),
            },
            "step_200_distributions": {
                "rows": int(step_200_indices.shape[0]),
                "opponent_land_count": _stats(step_200_opp_land),
                "own_land_count": _stats(step_200_own_land),
                "opponent_land_minus_own_land": _stats(step_200_land_advantage),
                "opponent_ahead_count": int((step_200_land_advantage > 0.0).sum()),
            },
            "expansion_timing": {
                "episodes_with_opponent_land_gt_1": _first_step_summary(first_expansion_steps),
                "episodes_with_opponent_land_gt_own_land": _first_step_summary(first_land_advantage_steps),
            },
            "rule_hit_counts": {
                "livestock_heavy_episodes": int((final_livestock > 8.0).sum()),
                "crop_heavy_episodes": int((final_strawberry > 20.0).sum()),
                "aggressive_expand_episodes": int((step_200_land_advantage > 0.0).sum()),
                "market_manipulator_episodes": None,
            },
            "market_telemetry": market_telemetry,
            "genuinely_derivable_archetypes_from_current_dataset": _derivable_archetypes(
                final_livestock,
                final_strawberry,
                step_200_land_advantage,
                market_telemetry,
            ),
            "conclusion": _conclusion(final_livestock, final_strawberry, step_200_land_advantage, market_telemetry),
        }
        return report


def write_reports(report: dict[str, Any], output_path: Path, markdown_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path.write_text(_to_markdown(report), encoding="utf-8")


def _validate_dataset(
    features: np.ndarray,
    opponent_features: np.ndarray,
    episode_ids: np.ndarray,
    steps: np.ndarray,
    terminals: np.ndarray,
) -> None:
    if features.ndim != 2 or features.shape[1] != 128 or features.dtype != np.float32:
        raise AssertionError(f"invalid features contract: shape={features.shape} dtype={features.dtype}")
    if opponent_features.shape != (features.shape[0], 24) or opponent_features.dtype != np.float32:
        raise AssertionError(f"invalid opponent_features contract: shape={opponent_features.shape} dtype={opponent_features.dtype}")
    if not np.allclose(opponent_features, features[:, 60:84]):
        raise AssertionError("opponent_features does not match features[:, 60:84]")
    if episode_ids.shape != (features.shape[0],) or episode_ids.dtype != np.int32:
        raise AssertionError("invalid episode_ids contract")
    if steps.shape != (features.shape[0],) or steps.dtype != np.int16:
        raise AssertionError("invalid steps contract")
    if terminals.shape != (features.shape[0],) or terminals.dtype != np.bool_:
        raise AssertionError("invalid terminals contract")
    if int(terminals.sum()) != len(np.unique(episode_ids)):
        raise AssertionError("terminal count does not match episode count")


def _stats(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {"count": 0}
    percentiles = np.percentile(values.astype(np.float64), [0, 5, 25, 50, 75, 95, 100])
    return {
        "count": int(values.size),
        "min": round(float(percentiles[0]), 6),
        "p05": round(float(percentiles[1]), 6),
        "p25": round(float(percentiles[2]), 6),
        "median": round(float(percentiles[3]), 6),
        "p75": round(float(percentiles[4]), 6),
        "p95": round(float(percentiles[5]), 6),
        "max": round(float(percentiles[6]), 6),
        "mean": round(float(np.mean(values)), 6),
        "nonzero_count": int((values != 0).sum()),
        "unique_values": _unique_values(values),
    }


def _unique_values(values: np.ndarray, limit: int = 20) -> list[dict[str, Any]]:
    rounded = np.round(values.astype(np.float64), 6)
    unique, counts = np.unique(rounded, return_counts=True)
    rows = [{"value": float(value), "count": int(count)} for value, count in zip(unique[:limit], counts[:limit])]
    if unique.shape[0] > limit:
        rows.append({"value": "...", "count": int(unique.shape[0] - limit)})
    return rows


def _opponent_pool_counts(opponent_ids: np.ndarray | None) -> dict[str, int]:
    if opponent_ids is None:
        return {}
    decoded = np.asarray([_row_text(row) for row in opponent_ids])
    unique, counts = np.unique(decoded, return_counts=True)
    return {str(name): int(count) for name, count in zip(unique, counts)}


def _market_telemetry(data_files: tuple[str, ...]) -> dict[str, Any]:
    opponent_actions_available = "opponent_actions_json" in data_files
    return {
        "global_market_prices_available": False,
        "expert_raw_actions_available": "raw_actions_json" in data_files,
        "expert_executed_actions_available": "actions_json" in data_files,
        "opponent_actions_available": opponent_actions_available,
        "opponent_sell_patterns_available": opponent_actions_available,
        "note": "Opponent action telemetry is available for sell-pattern analysis."
        if opponent_actions_available
        else "This dataset stores APEX4 expert actions, not opponent actions. Global prices were embedded into features, but opponent sell orders were not recorded.",
    }


def _first_steps_where(episode_ids: np.ndarray, steps: np.ndarray, mask: np.ndarray) -> np.ndarray:
    first_steps = []
    for episode_id in np.unique(episode_ids):
        indices = np.flatnonzero((episode_ids == episode_id) & mask)
        if indices.size:
            first_steps.append(int(steps[indices[0]]))
    return np.asarray(first_steps, dtype=np.int16)


def _first_step_summary(first_steps: np.ndarray) -> dict[str, Any]:
    if first_steps.size == 0:
        return {"count": 0, "min": None, "median": None, "max": None}
    return {
        "count": int(first_steps.size),
        "min": int(first_steps.min()),
        "median": float(np.median(first_steps)),
        "max": int(first_steps.max()),
    }


def _derivable_archetypes(
    final_livestock: np.ndarray,
    final_strawberry: np.ndarray,
    step_200_land_advantage: np.ndarray,
    market_telemetry: dict[str, Any],
) -> dict[str, bool]:
    return {
        "LIVESTOCK_HEAVY": bool((final_livestock > 8.0).any()),
        "CROP_HEAVY": bool((final_strawberry > 20.0).any()),
        "BALANCED": True,
        "AGGRESSIVE_EXPAND": bool((step_200_land_advantage > 0.0).any()),
        "MARKET_MANIPULATOR": False,
    }


def _conclusion(
    final_livestock: np.ndarray,
    final_strawberry: np.ndarray,
    step_200_land_advantage: np.ndarray,
    market_telemetry: dict[str, Any],
) -> dict[str, Any]:
    blockers = []
    if not (final_livestock > 8.0).any():
        blockers.append("No episode exceeds the livestock-heavy threshold.")
    if not (final_strawberry > 20.0).any():
        blockers.append("No episode exceeds the crop-heavy strawberry threshold.")
    if not (step_200_land_advantage > 0.0).any():
        blockers.append("No episode has opponent land greater than own land at step 200.")
    if market_telemetry["opponent_sell_patterns_available"]:
        blockers.append("Opponent sell-pattern telemetry exists, but no conservative MARKET_MANIPULATOR threshold is defined yet.")
    else:
        blockers.append("Opponent sell-pattern telemetry is unavailable, so MARKET_MANIPULATOR cannot be labeled.")
    telemetry_cause = (
        "Opponent action telemetry is now available, but MARKET_MANIPULATOR still needs a conservative rule."
        if market_telemetry["opponent_sell_patterns_available"]
        else "Market-manipulator labeling requires opponent action telemetry that was not captured in this dataset."
    )
    return {
        "step4_classifier_training_ready": False,
        "diagnosis": "The current Step 2 dataset is valid but does not contain genuine multi-class opponent archetype evidence.",
        "likely_causes": [
            "The selected opponent pool did not create observable archetype diversity under the current feature/label rules.",
            "The recorded opponent public-state features do not hit the crop-heavy or aggressive-expansion thresholds.",
            telemetry_cause,
        ],
        "blockers": blockers,
        "recommended_next_step": "Collect a targeted Step 3B/Step 2B dataset with real executable archetype opponents and record opponent action telemetry before retraining labels.",
    }


def _to_markdown(report: dict[str, Any]) -> str:
    td = report["transition_distributions"]
    fd = report["terminal_distributions"]
    s200 = report["step_200_distributions"]
    mt = report["market_telemetry"]
    hits = report["rule_hit_counts"]
    lines = [
        "# Step 3B Label Diagnostics",
        "",
        f"Source dataset: `{report['source_dataset']}`",
        f"Transitions: `{report['total_transitions']}`",
        f"Episodes: `{report['total_episodes']}`",
        "",
        "## Rule Hit Counts",
        "",
        f"- LIVESTOCK_HEAVY episodes: `{hits['livestock_heavy_episodes']}`",
        f"- CROP_HEAVY episodes: `{hits['crop_heavy_episodes']}`",
        f"- AGGRESSIVE_EXPAND episodes: `{hits['aggressive_expand_episodes']}`",
        "- MARKET_MANIPULATOR episodes: `not derivable`",
        "",
        "## Key Observed Maxima",
        "",
        f"- Max opponent cows + sheep, any transition: `{td['opponent_cows_plus_sheep']['max']}`",
        f"- Max final opponent cows + sheep: `{fd['final_opponent_cows_plus_sheep']['max']}`",
        f"- Max opponent strawberry tiles, any transition: `{td['opponent_strawberry_tiles']['max']}`",
        f"- Max final opponent strawberry tiles: `{fd['final_opponent_strawberry_tiles']['max']}`",
        f"- Max opponent land count, any transition: `{td['opponent_land_count']['max']}`",
        f"- Step 200 opponent-ahead count: `{s200['opponent_ahead_count']}`",
        f"- Max opponent worker count: `{td['opponent_worker_count']['max']}`",
        "",
        "## Market Telemetry",
        "",
        f"- Expert raw actions available: `{mt['expert_raw_actions_available']}`",
        f"- Expert executed actions available: `{mt['expert_executed_actions_available']}`",
        f"- Opponent actions available: `{mt['opponent_actions_available']}`",
        f"- Opponent sell patterns available: `{mt['opponent_sell_patterns_available']}`",
        "",
        "## Conclusion",
        "",
        report["conclusion"]["diagnosis"],
        "",
        "Step 4 remains blocked.",
    ]
    return "\n".join(lines) + "\n"


def _row_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Step 3 opponent-label diversity.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = diagnose_labels(args.input)
    write_reports(report, args.output, args.markdown)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
