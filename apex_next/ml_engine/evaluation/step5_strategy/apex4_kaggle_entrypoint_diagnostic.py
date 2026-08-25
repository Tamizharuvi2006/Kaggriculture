"""Isolated diagnostic for the original Kaggle-style APEX4 entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import kaggle_environments

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ORIGINAL_KAGGLE_ENTRYPOINT = PROJECT_ROOT / "apex_next" / "apex4" / "candidate" / "candidate_submission.py"
CERTIFIED_ENTRYPOINT = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
BASELINE_ENTRYPOINT = PROJECT_ROOT / "submission.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _obs(state: Any) -> dict[str, Any]:
    value = getattr(state, "observation", None)
    return value if isinstance(value, dict) else {}


def _compact_state(state: Any, player: int) -> dict[str, Any]:
    obs = _obs(state[player])
    farms = obs.get("farms", [])
    # Kaggriculture observations are seat-relative: farms[0] is the observing
    # player's own farm, including for seat 1.
    farm = farms[0] if isinstance(farms, list) and farms else {}
    return {
        "money": farm.get("money") if isinstance(farm, dict) else None,
        "workers": farm.get("workers") if isinstance(farm, dict) else None,
        "animals": farm.get("animals") if isinstance(farm, dict) else None,
        "land": farm.get("land") if isinstance(farm, dict) else None,
        "hands": farm.get("hands") if isinstance(farm, dict) else None,
        "tiles": farm.get("tiles") if isinstance(farm, dict) else None,
    }


def _run_one(seed: int, candidate_path: Path, baseline_path: Path) -> dict[str, Any]:
    candidate = _load(candidate_path, f"original_apex4_candidate_{seed}")
    baseline = _load(baseline_path, f"frozen_baseline_{seed}")
    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed},
    )
    state = env.reset(num_agents=2)
    rows: list[dict[str, Any]] = []
    for step in range(719):
        action0 = candidate.agent(_obs(state[0]), env.configuration)
        action1 = baseline.agent(_obs(state[1]), env.configuration)
        rows.append(
            {
                "step": step,
                "candidate_action": action0,
                "baseline_action": action1,
                "candidate_state_before": _compact_state(state, 0),
                "baseline_state_before": _compact_state(state, 1),
            }
        )
        state = env.step([action0, action1])
        if all(bool(getattr(item, "status", None) == "done") for item in state):
            break
    final = {
        "candidate": _compact_state(state, 0),
        "baseline": _compact_state(state, 1),
        "candidate_reward": getattr(state[0], "reward", None),
        "baseline_reward": getattr(state[1], "reward", None),
    }
    return {
        "seed": seed,
        "transitions": len(rows),
        "completed": len(rows) == 719,
        "final": final,
        "rows": rows,
    }


def run(seed_start: int, episodes: int, output: Path) -> dict[str, Any]:
    candidate = _load(ORIGINAL_KAGGLE_ENTRYPOINT, "original_apex4_metadata")
    report = {
        "status": "PASS",
        "diagnostic": "original Kaggle-style APEX4 entrypoint isolation",
        "environment": "kaggriculture",
        "configuration": {"episodeSteps": 720, "townCenterSellInterval": 24},
        "candidate_entrypoint": str(ORIGINAL_KAGGLE_ENTRYPOINT),
        "candidate_sha256": _sha256(ORIGINAL_KAGGLE_ENTRYPOINT),
        "certified_entrypoint": str(CERTIFIED_ENTRYPOINT),
        "certified_sha256": _sha256(CERTIFIED_ENTRYPOINT),
        "baseline_entrypoint": str(BASELINE_ENTRYPOINT),
        "baseline_sha256": _sha256(BASELINE_ENTRYPOINT),
        "candidate_default_strategy": getattr(candidate, "DEFAULT_STRATEGY", None),
        "seed_start": seed_start,
        "episodes": episodes,
        "results": [_run_one(seed_start + idx, ORIGINAL_KAGGLE_ENTRYPOINT, BASELINE_ENTRYPOINT) for idx in range(episodes)],
        "sealed_production_modified": False,
    }
    report["completed_episodes"] = sum(item["completed"] for item in report["results"])
    report["transition_counts"] = [item["transitions"] for item in report["results"]]
    report["status"] = "PASS" if report["completed_episodes"] == episodes else "FAIL"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=68000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "step5b" / "apex4_kaggle_entrypoint_diagnostic.json",
    )
    args = parser.parse_args()
    report = run(args.seed_start, args.episodes, args.output)
    print(json.dumps({key: report[key] for key in ("status", "candidate_entrypoint", "candidate_sha256", "completed_episodes", "transition_counts")}, indent=2))


if __name__ == "__main__":
    main()
