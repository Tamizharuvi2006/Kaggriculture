"""Compare the single-file PPO entrypoint and sealed v18 on Kaggle seed 0."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(env):
    final = env.steps[-1] if env.steps else []
    rows = []
    for entry in final[:2]:
        obs = entry.get("observation", {})
        farms = obs.get("farms", []) if isinstance(obs, dict) else []
        farm = farms[0] if farms else {}
        rows.append({
            "reward": entry.get("reward"),
            "status": entry.get("status"),
            "money": farm.get("money"),
            "farmer": farm.get("farmer"),
            "hands_count": len(farm.get("hands", [])) if isinstance(farm, dict) else None,
            "unlocked_quadrants": farm.get("unlocked_quadrants") if isinstance(farm, dict) else None,
            "shed": farm.get("shed") if isinstance(farm, dict) else None,
            "tiles": farm.get("tiles") if isinstance(farm, dict) else None,
        })
    return {"steps": len(env.steps), "players": rows}


def main() -> None:
    import kaggle_environments

    single = _load(ROOT / "release_packages/APEX4_PPO_FINAL_SINGLE.py", "seed0_single")
    sealed = _load(ROOT / "APEX4_SUBMISSION_FINAL.py", "seed0_sealed")
    noop = lambda observation, configuration=None: {"farmer": ["PASS"], "hands": [], "market": []}
    results = {}
    for name, own in (("ppo_vs_sealed", single.agent), ("sealed_vs_sealed", sealed.agent)):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0})
        errors = []
        try:
            env.run([own, sealed.agent if name == "ppo_vs_sealed" else noop])
        except Exception as exc:
            errors.append(repr(exc))
        results[name] = {"errors": errors, "summary": _summary(env)}
    report = {
        "status": "PASS" if all(not value["errors"] and value["summary"]["steps"] == 720 for value in results.values()) else "FAIL",
        "seed": 0,
        "configuration": {"environment": "kaggle_environments", "episodeSteps": 720},
        "results": results,
    }
    output = ROOT / "reports/step5b/seed0_single_vs_sealed_diagnostic.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    compact = {}
    for key, value in results.items():
        players = value["summary"]["players"]
        compact[key] = {
            "steps": value["summary"]["steps"],
            "errors": value["errors"],
            "rewards": [player.get("reward") for player in players],
            "money": [player.get("money") for player in players],
            "unlocked_quadrants": [player.get("unlocked_quadrants") for player in players],
        }
    print(json.dumps({"status": report["status"], "results": compact}, indent=2))


if __name__ == "__main__":
    main()
