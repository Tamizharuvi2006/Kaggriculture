"""Compare fixed-v18 and dynamic APEX4 action paths on matched real games."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import kaggle_environments

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APEX4_PATH = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
BASELINE_PATH = PROJECT_ROOT / "submission.py"
PROFILES = {
    "BALANCED": {"cows": 8, "sheep": 6, "cash_reserve": 150, "animal_daily_cap": 3, "force_expert": None},
    "LIVESTOCK": {"cows": 12, "sheep": 2, "cash_reserve": 150, "animal_daily_cap": 3, "force_expert": "COW_RUSH"},
    "PREMIUM": {"cows": 8, "sheep": 6, "cash_reserve": 250, "animal_daily_cap": 3, "force_expert": "PREMIUM_CROP"},
    "WHEAT_RUSH": {"cows": 12, "sheep": 2, "cash_reserve": 150, "animal_daily_cap": 1, "force_expert": "WHEAT_RUSH"},
}


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


def _obs(state_item: Any) -> dict[str, Any]:
    value = getattr(state_item, "observation", None)
    return value if isinstance(value, dict) else {}


def _digest_action(action: Any) -> str:
    payload = json.dumps(action, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _farm_digest(obs: dict[str, Any]) -> str:
    farms = obs.get("farms", [])
    own = farms[0] if isinstance(farms, list) and farms else {}
    payload = {"farm": own, "market": obs.get("market", {})}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _make_agent(name: str, mode: str, overrides: dict[str, Any]) -> Any:
    module = _load(APEX4_PATH, f"apex4_{mode}_{name}_{id(overrides)}")
    config = dict(overrides)
    if mode == "fixed_v18":
        config.update({"use_fixed_schedule": True, "fixed_schedule_version": "v18"})
    else:
        config["use_fixed_schedule"] = False
    module.configure_strategy(config)
    return module


def _run(seed: int, profile_name: str, mode: str) -> dict[str, Any]:
    overrides = PROFILES[profile_name]
    candidate = _make_agent(profile_name, mode, overrides)
    baseline = _load(BASELINE_PATH, f"baseline_{profile_name}_{mode}_{seed}")
    env = kaggle_environments.make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "townCenterSellInterval": 24, "seed": seed},
    )
    state = env.reset(num_agents=2)
    rows: list[dict[str, Any]] = []
    event_counts: Counter[str] = Counter()
    for step in range(719):
        obs = _obs(state[0])
        action = candidate.agent(obs, env.configuration)
        baseline_action = baseline.agent(_obs(state[1]), env.configuration)
        for order in action.get("market", []) if isinstance(action, dict) else []:
            if order:
                event_counts[str(order[0])] += 1
        rows.append(
            {
                "step": step,
                "action_hash": _digest_action(action),
                "action": action,
                "state_digest": _farm_digest(obs),
                "baseline_action_hash": _digest_action(baseline_action),
            }
        )
        state = env.step([action, baseline_action])
        if all(bool(getattr(item, "status", None) == "done") for item in state):
            break
    final_obs = _obs(state[0])
    farms = final_obs.get("farms", [])
    own = farms[0] if isinstance(farms, list) and farms else {}
    return {
        "seed": seed,
        "profile": profile_name,
        "mode": mode,
        "transitions": len(rows),
        "completed": len(rows) == 719,
        "event_counts": dict(sorted(event_counts.items())),
        "final_money": own.get("money") if isinstance(own, dict) else None,
        "final_state_digest": _farm_digest(final_obs),
        "rows": rows,
    }


def _diff(fixed: dict[str, Any], dynamic: dict[str, Any]) -> dict[str, Any]:
    fixed_rows = fixed["rows"]
    dynamic_rows = dynamic["rows"]
    differing = [idx for idx, (a, b) in enumerate(zip(fixed_rows, dynamic_rows)) if a["action_hash"] != b["action_hash"]]
    state_differing = [idx for idx, (a, b) in enumerate(zip(fixed_rows, dynamic_rows)) if a["state_digest"] != b["state_digest"]]
    samples = []
    for idx in differing[:5]:
        samples.append({"step": idx, "fixed_action": fixed_rows[idx]["action"], "dynamic_action": dynamic_rows[idx]["action"]})
    return {
        "first_action_difference": differing[0] if differing else None,
        "last_action_difference": differing[-1] if differing else None,
        "action_difference_count": len(differing),
        "first_state_difference": state_differing[0] if state_differing else None,
        "state_difference_count": len(state_differing),
        "samples": samples,
    }


def run(seed_start: int, episodes: int, output: Path) -> dict[str, Any]:
    seeds = [seed_start + idx for idx in range(episodes)]
    comparisons = []
    for profile_name in PROFILES:
        for seed in seeds:
            fixed = _run(seed, profile_name, "fixed_v18")
            dynamic = _run(seed, profile_name, "dynamic")
            comparisons.append(
                {
                    "seed": seed,
                    "profile": profile_name,
                    "fixed": {key: fixed[key] for key in ("transitions", "completed", "event_counts", "final_money", "final_state_digest")},
                    "dynamic": {key: dynamic[key] for key in ("transitions", "completed", "event_counts", "final_money", "final_state_digest")},
                    "diff": _diff(fixed, dynamic),
                }
            )
    report = {
        "status": "PASS",
        "diagnostic": "fixed v18 versus dynamic APEX4 action pipeline",
        "source": str(APEX4_PATH),
        "source_sha256": _sha256(APEX4_PATH),
        "baseline": str(BASELINE_PATH),
        "seed_start": seed_start,
        "episodes": episodes,
        "profiles": PROFILES,
        "fixed_configuration": {"use_fixed_schedule": True, "fixed_schedule_version": "v18"},
        "dynamic_configuration": {"use_fixed_schedule": False},
        "comparisons": comparisons,
        "ppo_updates": False,
        "sealed_production_modified": False,
    }
    report["completed_runs"] = sum(item["fixed"]["completed"] and item["dynamic"]["completed"] for item in comparisons)
    report["status"] = "PASS" if report["completed_runs"] == episodes * len(PROFILES) else "FAIL"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=68000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "step5b" / "apex4_fixed_vs_dynamic_diagnostic.json")
    args = parser.parse_args()
    report = run(args.seed_start, args.episodes, args.output)
    print(json.dumps({"status": report["status"], "source_sha256": report["source_sha256"], "completed_runs": report["completed_runs"]}, indent=2))


if __name__ == "__main__":
    main()
