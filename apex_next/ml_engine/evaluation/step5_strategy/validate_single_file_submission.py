"""Validate the self-contained entrypoint against the validated multi-file candidate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _match(single_path: Path, package_dir: Path, seed: int, index: int) -> dict:
    import kaggle_environments

    single = _load(single_path, f"single_{seed}_{index}")
    sys.path.insert(0, str(package_dir))
    try:
        candidate = _load(package_dir / "APEX4_PPO_CANDIDATE.py", f"candidate_{seed}_{index}")
        sealed = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"sealed_{seed}_{index}")
    finally:
        if sys.path[0] == str(package_dir):
            sys.path.pop(0)

    env_single = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_candidate = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    errors = []
    try:
        env_single.run([single.agent, sealed.agent])
        env_candidate.run([candidate.agent, candidate._sealed.agent])
    except Exception as exc:
        errors.append(repr(exc))

    first = None
    limit = min(len(env_single.steps), len(env_candidate.steps))
    for step in range(limit):
        for player in (0, 1):
            left = env_single.steps[step][player]
            right = env_candidate.steps[step][player]
            if json.dumps(left, sort_keys=True, default=str) != json.dumps(right, sort_keys=True, default=str):
                first = {"step": step, "player": player, "single": left, "candidate": right}
                break
        if first is not None:
            break

    fallback_observation = {"step": 120}
    original_predict = single.predict
    single.predict = lambda _features: (_ for _ in ()).throw(RuntimeError("forced fallback test"))
    fallback_action = single.agent(fallback_observation, None)
    single.predict = original_predict
    expected_fallback = single._sealed.agent(fallback_observation, None)
    return {
        "seed": seed,
        "single_steps": len(env_single.steps),
        "candidate_steps": len(env_candidate.steps),
        "first_divergence": first,
        "same_trajectory": first is None and len(env_single.steps) == len(env_candidate.steps),
        "fallback_matches_sealed": fallback_action == expected_fallback,
        "errors": errors,
    }


def run(single: Path, package: Path, output: Path, seed_start: int, episodes: int) -> dict:
    import numpy as np

    with tempfile.TemporaryDirectory(prefix="apex4_single_validation_") as temp:
        isolated = Path(temp) / single.name
        shutil.copy2(single, isolated)
        with tempfile.TemporaryDirectory(prefix="apex4_multi_candidate_") as package_temp:
            package_dir = Path(package_temp)
            with zipfile.ZipFile(package) as archive:
                archive.extractall(package_dir)
            rows = [_match(isolated, package_dir, seed_start + i, i) for i in range(episodes)]

    report = {
        "status": "PASS" if all(row["same_trajectory"] and row["fallback_matches_sealed"] and not row["errors"] for row in rows) else "FAIL",
        "single_file": str(single),
        "reference_package": str(package),
        "isolated_import": True,
        "torch_required": False,
        "seed_start": seed_start,
        "episodes": episodes,
        "completed_720_pairs": sum(row["single_steps"] == 720 and row["candidate_steps"] == 720 for row in rows),
        "trajectory_divergences": sum(not row["same_trajectory"] for row in rows),
        "fallback_passes": sum(row["fallback_matches_sealed"] for row in rows),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=77000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.single, args.package, args.output, args.seed_start, args.episodes)
    print(json.dumps({k: report[k] for k in ("status", "isolated_import", "torch_required", "episodes", "completed_720_pairs", "trajectory_divergences", "fallback_passes")}, indent=2))


if __name__ == "__main__":
    main()
