"""Adaptive source gauntlet on seeds from historical Kaggle losses."""

from __future__ import annotations

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
SOURCES = {
    "L_PLUS": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_l_plus.py",
    "L_PLUS_PLUS": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_l_plus_plus.py",
    "HYBRID_L_PLUS": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_competitive_hybrid_v13.py",
    "APEX30": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_apex30.py",
    "APEX33": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_apex33.py",
    "APEX35": PROJECT_ROOT / "generalization_pipeline" / "submission_candidate_apex35.py",
}


def load_agent(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def match(own_path: Path, opponent_path: Path, seed: int, label: str, own_label: str, index: int) -> dict:
    import kaggle_environments

    own = load_agent(own_path, f"source_gauntlet_own_{label}_{own_label}_{index}")
    opponent = load_agent(opponent_path, f"source_gauntlet_opp_{label}_{index}")
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
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
        "historical_label": label,
        "seed": seed,
        "own": own_label,
        "opponent": str(opponent_path),
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
    selected = [r for r in records if r.get("old_model_lost")]
    with tempfile.TemporaryDirectory(prefix="old_source_gauntlet_") as temp:
        extracted = Path(temp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(extracted)
        candidate = extracted / "APEX4_PPO_FINAL_SINGLE.py"
        rows = []
        for index, record in enumerate(selected):
            label = record["historical_label"]
            source = SOURCES.get(label)
            if source is None or not source.exists():
                continue
            seed = int(record["seed"])
            rows.append(match(candidate, source, seed, label, "ppo_candidate", index))
            rows.append(match(APEX4_PATH, source, seed, label, "sealed_v18", index))

    summary = {}
    for label in sorted({r["historical_label"] for r in rows}):
        summary[label] = {}
        for own in ("ppo_candidate", "sealed_v18"):
            group = [r for r in rows if r["historical_label"] == label and r["own"] == own]
            summary[label][own] = {
                "games": len(group),
                "mean_mcv": float(np.mean([r["own_mcv"] for r in group])),
                "mean_margin": float(np.mean([r["margin"] for r in group])),
                "win_rate": float(np.mean([r["won"] for r in group])),
                "completed": int(sum(r["completed"] for r in group)),
            }
        ppo = [r for r in rows if r["historical_label"] == label and r["own"] == "ppo_candidate"]
        base = [r for r in rows if r["historical_label"] == label and r["own"] == "sealed_v18"]
        summary[label]["ppo_minus_sealed_mcv"] = float(np.mean([p["own_mcv"] - b["own_mcv"] for p, b in zip(ppo, base)]))

    report = {
        "status": "PASS" if rows and all(r["completed"] for r in rows) else "FAIL",
        "evaluation": "Frozen PPO and sealed v18 versus adaptive historical source candidates",
        "training": False,
        "submission": False,
        "source_mapping": {k: str(v) for k, v in SOURCES.items()},
        "note": "Hybrid uses the available competitive_hybrid_v13 source; verify exact historical submission identity separately.",
        "summary_by_model": summary,
        "rows": rows,
    }
    output = GAUNTLET / "old_source_gauntlet_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": len(rows), "summary_by_model": summary}, indent=2))
    print(f"WROTE {output}")


if __name__ == "__main__":
    main()
