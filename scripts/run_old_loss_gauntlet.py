"""Run frozen PPO and sealed APEX4 against historical losing-opponent traces.

The opponent is an open-loop replay of the exact opponent actions recorded by
Kaggle. Results are diagnostic evidence, not a claim that the opponent adapts
to the new player.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.training.collect_expert_demos import APEX4_PATH

GAUNTLET = PROJECT_ROOT / "reports" / "step5b" / "old_loss_gauntlet"
SUMMARY = GAUNTLET / "historical_replay_summary.json"
PACKAGE = PROJECT_ROOT / "release_packages" / "APEX4_PPO_FINAL_SINGLE_20260821.zip"


def load_agent(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def replay_agent(actions: list[dict]):
    def agent(observation, configuration=None):
        step = int(observation.get("step", 0))
        if 0 <= step < len(actions):
            return copy.deepcopy(actions[step])
        return {"farmer": ["PASS"], "hands": [], "market": []}

    return agent


def run_match(candidate_path: Path, sealed_path: Path, record: dict, use_candidate: bool) -> dict:
    import kaggle_environments

    replay_path = Path(record["replay_path"])
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    opponent_index = int(record["opponent_player_index"])
    opponent_actions = [step[opponent_index]["action"] for step in replay["steps"]]
    own = load_agent(candidate_path if use_candidate else sealed_path, f"gauntlet_own_{record['episode_id']}_{use_candidate}")
    opponent = replay_agent(opponent_actions)
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": record["seed"]})
    errors = []
    try:
        env.run([own, opponent])
    except Exception as exc:
        errors.append(repr(exc))
    last = env.steps[-1] if env.steps else []
    own_state = last[0] if len(last) > 0 else {}
    opponent_state = last[1] if len(last) > 1 else {}
    own_mcv = float(own_state.get("reward", 0.0))
    opponent_mcv = float(opponent_state.get("reward", 0.0))
    return {
        "historical_label": record["historical_label"],
        "historical_episode_id": record["episode_id"],
        "historical_seed": record["seed"],
        "historical_old_reward": record["old_reward"],
        "historical_opponent_reward": record["opponent_reward"],
        "player": "ppo_candidate" if use_candidate else "sealed_v18",
        "steps": len(env.steps),
        "completed": len(env.steps) == 720 and not errors,
        "own_mcv": own_mcv,
        "opponent_mcv": opponent_mcv,
        "margin": own_mcv - opponent_mcv,
        "won": own_mcv > opponent_mcv,
        "tied": own_mcv == opponent_mcv,
        "errors": errors,
    }


def main() -> None:
    records = json.loads(SUMMARY.read_text(encoding="utf-8"))["records"]
    loss_records = [r for r in records if r.get("old_model_lost")]
    with tempfile.TemporaryDirectory(prefix="old_loss_gauntlet_") as temp:
        extracted = Path(temp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(extracted)
        candidate_path = extracted / "APEX4_PPO_FINAL_SINGLE.py"
        rows = []
        for record in loss_records:
            rows.append(run_match(candidate_path, APEX4_PATH, record, True))
            rows.append(run_match(candidate_path, APEX4_PATH, record, False))

    summary = {}
    for label in sorted({r["historical_label"] for r in rows}):
        candidate = [r for r in rows if r["historical_label"] == label and r["player"] == "ppo_candidate"]
        baseline = [r for r in rows if r["historical_label"] == label and r["player"] == "sealed_v18"]
        summary[label] = {
            "games": len(candidate),
            "candidate_mean_mcv": float(np.mean([r["own_mcv"] for r in candidate])),
            "baseline_mean_mcv": float(np.mean([r["own_mcv"] for r in baseline])),
            "candidate_mean_margin": float(np.mean([r["margin"] for r in candidate])),
            "baseline_mean_margin": float(np.mean([r["margin"] for r in baseline])),
            "candidate_win_rate": float(np.mean([r["won"] for r in candidate])),
            "baseline_win_rate": float(np.mean([r["won"] for r in baseline])),
            "candidate_minus_baseline_mcv": float(np.mean([c["own_mcv"] - b["own_mcv"] for c, b in zip(candidate, baseline)])),
        }
    report = {
        "status": "PASS" if all(r["completed"] for r in rows) else "FAIL",
        "evaluation": "Frozen PPO and sealed v18 versus historical Kaggle losing-opponent action traces",
        "training": False,
        "submission": False,
        "opponent_mode": "open_loop_historical_replay_trace",
        "historical_loss_records": loss_records,
        "summary_by_model": summary,
        "rows": rows,
    }
    output = GAUNTLET / "old_loss_gauntlet_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": len(rows), "summary_by_model": summary}, indent=2))
    print(f"WROTE {output}")


if __name__ == "__main__":
    main()
