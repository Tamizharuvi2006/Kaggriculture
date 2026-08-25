"""Offline Kaggle-environments head-to-head for the PPO candidate package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _match(package_dir: Path, seed: int, index: int) -> dict:
    import kaggle_environments

    sys.path.insert(0, str(package_dir))
    try:
        candidate = _load(package_dir / "APEX4_PPO_CANDIDATE.py", f"candidate_{seed}_{index}")
        sealed = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"sealed_{seed}_{index}")
    finally:
        if sys.path[0] == str(package_dir):
            sys.path.pop(0)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    noop = lambda obs: {"farmer": ["PASS"], "hands": [], "market": []}
    errors = []
    try:
        env.run([candidate.agent, sealed.agent])
    except Exception as exc:  # pragma: no cover - recorded as a gate failure
        errors.append(str(exc))

    last = env.steps[-1] if env.steps else []
    candidate_state = last[0] if len(last) > 0 else {}
    sealed_state = last[1] if len(last) > 1 else {}
    candidate_mcv = float(candidate_state.get("reward", 0.0))
    sealed_mcv = float(sealed_state.get("reward", 0.0))
    return {
        "seed": seed,
        "steps": len(env.steps),
        "completed": len(env.steps) == 720 and not errors,
        "candidate_mcv": candidate_mcv,
        "sealed_mcv": sealed_mcv,
        "candidate_win": candidate_mcv > sealed_mcv,
        "sealed_win": sealed_mcv > candidate_mcv,
        "tie": candidate_mcv == sealed_mcv,
        "invalid_actions": 0 if not errors else None,
        "errors": errors,
    }


def run(package_zip: Path, output: Path, seed_start: int, episodes: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="apex4_candidate_eval_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(package_zip) as archive:
            archive.extractall(package_dir)
        rows = [_match(package_dir, seed_start + index, index) for index in range(episodes)]

    candidate = np.asarray([row["candidate_mcv"] for row in rows], dtype=np.float64)
    sealed = np.asarray([row["sealed_mcv"] for row in rows], dtype=np.float64)
    delta = candidate - sealed
    report = {
        "status": "PASS" if all(row["completed"] for row in rows) else "FAIL",
        "evaluation": "candidate ZIP versus sealed APEX4 direct Kaggle head-to-head",
        "package": str(package_zip),
        "seed_start": seed_start,
        "episodes": episodes,
        "inference_only": True,
        "training": False,
        "upload_executed": False,
        "candidate": {
            "mean_mcv": float(candidate.mean()),
            "std_mcv": float(candidate.std()),
            "win_rate": float(np.mean(candidate > sealed)),
        },
        "sealed_apex4": {
            "mean_mcv": float(sealed.mean()),
            "std_mcv": float(sealed.std()),
            "win_rate": float(np.mean(sealed > candidate)),
        },
        "paired_mcv_delta_candidate_minus_sealed": {
            "mean": float(delta.mean()),
            "std": float(delta.std()),
            "candidate_higher": int(np.sum(delta > 0)),
            "sealed_higher": int(np.sum(delta < 0)),
            "ties": int(np.sum(delta == 0)),
        },
        "completion": {
            "completed_720": sum(row["completed"] for row in rows),
            "invalid_actions": sum(row["invalid_actions"] or 0 for row in rows),
            "errors": sum(len(row["errors"]) for row in rows),
        },
        "per_seed": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=77000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.package, args.output, args.seed_start, args.episodes), indent=2))


if __name__ == "__main__":
    main()
