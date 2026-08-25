"""Step 1 acceptance runner for the real APEX 4.1 ML environment wrapper.

Runs complete PASS-only episodes through kaggle_environments and validates every
feature transition. This is an acceptance check, not training data generation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import PASS_ACTION, KaggricultureGymEnv, sanitize_action


REPORT_PATH = Path(__file__).resolve().parent / "step1_acceptance_report.json"


def run_acceptance(
    episodes: int = 10,
    seed_start: int = 1000,
    output_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Run full PASS-only episodes and write an evidence report."""

    started = time.perf_counter()
    episode_reports = []
    total_transitions = 0
    exceptions: list[dict[str, Any]] = []

    for episode_index in range(episodes):
        seed = seed_start + episode_index
        episode_started = time.perf_counter()
        report: dict[str, Any] = {
            "episode": episode_index,
            "seed": seed,
            "completed": False,
            "steps": 0,
            "reward": None,
            "exception": None,
            "feature_checks": {
                "shape_128": True,
                "dtype_float32": True,
                "finite": True,
                "action_format": True,
            },
        }

        try:
            env = KaggricultureGymEnv()
            initial_features = env.reset(seed=seed)
            _validate_features(initial_features)

            done = False
            reward = 0.0
            while not done:
                action = sanitize_action(PASS_ACTION)
                _validate_action(action)
                features, reward, done, info = env.step(action)
                _validate_features(features)
                _validate_action(info["our_action"])
                _validate_action(info["opponent_action"])
                report["steps"] = int(info["step"])
                total_transitions += 1

                if report["steps"] > 720:
                    raise AssertionError(f"episode exceeded 720 steps: {report['steps']}")

            report["completed"] = True
            report["reward"] = float(reward)
        except Exception as exc:  # noqa: BLE001 - report exact acceptance failure.
            report["exception"] = repr(exc)
            exceptions.append({"episode": episode_index, "seed": seed, "exception": repr(exc)})

        report["elapsed_seconds"] = round(time.perf_counter() - episode_started, 6)
        episode_reports.append(report)

    summary = {
        "status": "PASS" if not exceptions and all(ep["completed"] for ep in episode_reports) else "FAIL",
        "episodes_requested": episodes,
        "episodes_completed": sum(1 for ep in episode_reports if ep["completed"]),
        "total_transitions": total_transitions,
        "max_transitions_allowed": episodes * 720,
        "observed_step_counts": [ep["steps"] for ep in episode_reports],
        "exceptions": exceptions,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "environment": "kaggle_environments.make('kaggriculture')",
        "our_policy": "PASS_ONLY",
        "opponent": "submission.py via KaggricultureGymEnv default opponent_path",
        "checks": [
            "features.shape == (128,)",
            "features.dtype == np.float32",
            "np.isfinite(features).all()",
            "sanitized action has farmer/hands/market keys",
            "market order count <= 10",
        ],
        "episodes": episode_reports,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _validate_features(features: np.ndarray) -> None:
    if features.shape != (128,):
        raise AssertionError(f"expected feature shape (128,), got {features.shape}")
    if features.dtype != np.float32:
        raise AssertionError(f"expected feature dtype float32, got {features.dtype}")
    if not np.isfinite(features).all():
        raise AssertionError("features contain NaN or Inf")


def _validate_action(action: dict[str, Any]) -> None:
    if set(action) != {"farmer", "hands", "market"}:
        raise AssertionError(f"invalid action keys: {sorted(action)}")
    if not isinstance(action["farmer"], list) or len(action["farmer"]) < 1:
        raise AssertionError(f"invalid farmer action: {action['farmer']}")
    if not isinstance(action["hands"], list):
        raise AssertionError(f"invalid hands action: {action['hands']}")
    if not isinstance(action["market"], list) or len(action["market"]) > 10:
        raise AssertionError(f"invalid market action count: {action['market']}")
    for order in action["market"]:
        if not isinstance(order, list):
            raise AssertionError(f"market order is not a list: {order!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run APEX 4.1 ML Step 1 acceptance.")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    summary = run_acceptance(episodes=args.episodes, seed_start=args.seed_start, output_path=args.output)
    print(json.dumps({key: value for key, value in summary.items() if key != "episodes"}, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
