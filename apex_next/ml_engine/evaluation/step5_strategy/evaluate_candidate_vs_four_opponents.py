"""Frozen tournament: packaged PPO candidate and sealed APEX4 versus four opponents."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.training.collect_expert_demos import (
    APEX35_PATH,
    APEX4_PATH,
    V18_PATH,
    _pass_agent,
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opponent_factory(opponent_id: str, index: int):
    if opponent_id == "pass_only":
        return _pass_agent
    paths = {
        "apex35_live_submission": APEX35_PATH,
        "apex4_self_play": APEX4_PATH,
        "v18_baseline": V18_PATH,
    }
    return _load(paths[opponent_id], f"opponent_{opponent_id}_{index}").agent


def _match(package_dir: Path, opponent_id: str, seed: int, index: int, candidate_side: bool) -> dict:
    import kaggle_environments

    sys.path.insert(0, str(package_dir))
    try:
        candidate = _load(package_dir / "APEX4_PPO_CANDIDATE.py", f"candidate_tournament_{index}")
        sealed = _load(package_dir / "APEX4_SUBMISSION_FINAL.py", f"sealed_tournament_{index}")
    finally:
        if sys.path[0] == str(package_dir):
            sys.path.pop(0)

    own = candidate.agent if candidate_side else sealed.agent
    opponent = _opponent_factory(opponent_id, index)
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    errors = []
    try:
        env.run([own, opponent])
    except Exception as exc:
        errors.append(repr(exc))
    last = env.steps[-1] if env.steps else []
    own_state = last[0] if len(last) > 0 else {}
    opp_state = last[1] if len(last) > 1 else {}
    own_mcv = float(own_state.get("reward", 0.0))
    opp_mcv = float(opp_state.get("reward", 0.0))
    return {
        "opponent": opponent_id,
        "seed": seed,
        "candidate_side": candidate_side,
        "steps": len(env.steps),
        "completed": len(env.steps) == 720 and not errors,
        "own_mcv": own_mcv,
        "opponent_mcv": opp_mcv,
        "won": own_mcv > opp_mcv,
        "invalid_actions": 0 if not errors else None,
        "errors": errors,
    }


def run(package: Path, output: Path, seed_start: int, games_per_opponent: int) -> dict:
    opponent_ids = ["apex35_live_submission", "apex4_self_play", "v18_baseline", "pass_only"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="apex4_four_opponents_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(package) as archive:
            archive.extractall(package_dir)
        for opponent_index, opponent_id in enumerate(opponent_ids):
            for game_index in range(games_per_opponent):
                seed = seed_start + opponent_index * games_per_opponent + game_index
                rows.append(_match(package_dir, opponent_id, seed, len(rows), True))
                rows.append(_match(package_dir, opponent_id, seed, len(rows), False))

    by_opponent = {}
    for opponent_id in opponent_ids:
        candidate = [r for r in rows if r["opponent"] == opponent_id and r["candidate_side"]]
        baseline = [r for r in rows if r["opponent"] == opponent_id and not r["candidate_side"]]
        c = np.asarray([r["own_mcv"] for r in candidate], dtype=np.float64)
        b = np.asarray([r["own_mcv"] for r in baseline], dtype=np.float64)
        by_opponent[opponent_id] = {
            "games": len(candidate),
            "candidate_mean_mcv": float(c.mean()),
            "sealed_mean_mcv": float(b.mean()),
            "candidate_win_rate": float(np.mean([r["won"] for r in candidate])),
            "sealed_win_rate": float(np.mean([r["won"] for r in baseline])),
            "candidate_minus_sealed_mcv": float((c - b).mean()),
            "candidate_wins": int(sum(r["won"] for r in candidate)),
            "sealed_wins": int(sum(r["won"] for r in baseline)),
            "ties": int(sum(r["own_mcv"] == r["opponent_mcv"] for r in candidate)),
            "completed_candidate": int(sum(r["completed"] for r in candidate)),
            "completed_sealed": int(sum(r["completed"] for r in baseline)),
            "invalid_actions": int(sum(r["invalid_actions"] or 0 for r in candidate + baseline)),
        }

    report = {
        "status": "PASS" if all(r["completed"] for r in rows) else "FAIL",
        "evaluation": "packaged PPO candidate versus sealed APEX4 against four Kaggriculture opponents",
        "package": str(package),
        "opponents": opponent_ids,
        "games_per_opponent": games_per_opponent,
        "seed_start": seed_start,
        "training": False,
        "upload_executed": False,
        "summary_by_opponent": by_opponent,
        "total_completed": sum(r["completed"] for r in rows),
        "total_games": len(rows),
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=78000)
    parser.add_argument("--games-per-opponent", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.package, args.output, args.seed_start, args.games_per_opponent)
    print(json.dumps({k: report[k] for k in ("status", "opponents", "games_per_opponent", "total_completed", "total_games", "summary_by_opponent")}, indent=2))


if __name__ == "__main__":
    main()
