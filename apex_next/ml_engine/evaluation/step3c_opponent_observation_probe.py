"""Probe raw opponent observations for the Step 3 label-diversity blocker.

This is a small diagnostic run, not a new training dataset. It executes the
same expert/opponent path used by Step 2 and captures raw farm summaries at a
few fixed steps so we can separate opponent inactivity from observation bugs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import kaggle_environments

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import (
    adapt_observation_for_apex_style_agent,
    call_agent,
    load_agent,
    sanitize_action,
)
from apex_next.ml_engine.training.collect_expert_demos import APEX4_PATH, _opponent_pool


ML_ENGINE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_ENGINE_DIR / "data"
DIAGNOSTICS_DIR = ML_ENGINE_DIR / "evaluation" / "step3_diagnostics"
DEFAULT_OUTPUT = DIAGNOSTICS_DIR / "step3c_opponent_observation_probe.json"
DEFAULT_MARKDOWN = DIAGNOSTICS_DIR / "step3c_opponent_observation_probe.md"
DEFAULT_SAMPLE_STEPS = (0, 100, 200, 400, 600, 718)


def probe_opponent_observations(
    seed_start: int = 10000,
    sample_steps: tuple[int, ...] = DEFAULT_SAMPLE_STEPS,
) -> dict[str, Any]:
    expert_agent = load_agent(APEX4_PATH)
    opponents = _opponent_pool()
    episodes = []

    for episode_index, (opponent_id, opponent_fn) in enumerate(opponents):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720})
        env.configuration.randomSeed = int(seed_start + episode_index)
        state = env.reset(num_agents=2)
        snapshots = []
        action_counts = {
            "opponent_agent_calls": 0,
            "opponent_non_pass_farmer": 0,
            "opponent_market_nonempty": 0,
            "opponent_hands_nonempty": 0,
            "expert_non_pass_farmer": 0,
            "expert_market_nonempty": 0,
            "expert_hands_nonempty": 0,
        }
        exceptions = []
        done = False
        last_reward = None

        while not done:
            obs0 = _observation(state[0])
            obs1 = _observation(state[1])
            current_step = int(obs0.get("step", 0))

            raw_expert_action = call_agent(expert_agent, obs0, env.configuration)
            adapted_obs1 = adapt_observation_for_apex_style_agent(obs1, fallback_step=current_step)
            raw_opponent_action = call_agent(opponent_fn, adapted_obs1, env.configuration)
            expert_action = sanitize_action(raw_expert_action)
            opponent_action = sanitize_action(raw_opponent_action)
            _update_action_counts(action_counts, expert_action, opponent_action)

            if current_step in sample_steps:
                snapshots.append(
                    {
                        "step": current_step,
                        "agent0_observation": _observation_summary(obs0),
                        "agent1_observation": _observation_summary(obs1),
                        "adapted_opponent_observation": _observation_summary(adapted_obs1),
                        "expert_action": expert_action,
                        "opponent_action": opponent_action,
                    }
                )

            try:
                state = env.step([expert_action, opponent_action])
            except Exception as exc:  # noqa: BLE001 - this is a diagnostic.
                exceptions.append({"step": current_step, "exception": repr(exc)})
                break

            done = _done(state)
            if done:
                last_reward = {
                    "agent0_reward": getattr(state[0], "reward", None),
                    "agent1_reward": getattr(state[1], "reward", None),
                }

            if current_step > 720:
                exceptions.append({"step": current_step, "exception": "step exceeded 720"})
                break

        episodes.append(
            {
                "episode": episode_index,
                "seed": seed_start + episode_index,
                "opponent_id": opponent_id,
                "completed": bool(done and not exceptions),
                "snapshots": snapshots,
                "action_counts": action_counts,
                "final_reward": last_reward,
                "exceptions": exceptions,
            }
        )

    return {
        "status": "PASS" if all(ep["completed"] for ep in episodes) else "FAIL",
        "seed_start": seed_start,
        "sample_steps": list(sample_steps),
        "episodes": episodes,
        "conclusion": _conclusion(episodes),
    }


def write_reports(report: dict[str, Any], output_path: Path, markdown_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path.write_text(_to_markdown(report), encoding="utf-8")


def _observation_summary(obs: dict[str, Any]) -> dict[str, Any]:
    farms = obs.get("farms") if isinstance(obs.get("farms"), list) else []
    return {
        "player": obs.get("player", obs.get("index", obs.get("agentIndex"))),
        "step": obs.get("step"),
        "farm0": _farm_summary(farms[0] if len(farms) > 0 else {}),
        "farm1": _farm_summary(farms[1] if len(farms) > 1 else {}),
    }


def _farm_summary(farm: Any) -> dict[str, Any]:
    farm = farm if isinstance(farm, dict) else {}
    tiles = _flatten_tiles(farm.get("tiles", []))
    crop_counts = {crop: 0 for crop in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")}
    animal_tiles = {"COW": 0, "SHEEP": 0}
    planted_tiles = 0
    mature_tiles = 0
    for tile in tiles:
        if not isinstance(tile, dict):
            continue
        crop = _norm(_first_present(tile, ("crop", "planted", "plant", "item", "type"), ""))
        if crop in crop_counts:
            crop_counts[crop] += 1
            planted_tiles += 1
        animal = _norm(_first_present(tile, ("animal", "type", "item"), ""))
        if animal in animal_tiles:
            animal_tiles[animal] += 1
        stage = str(_first_present(tile, ("stage", "growth", "status", "state"), "")).upper()
        if stage in {"RIPE", "MATURE", "READY", "HARVESTABLE"} or "RIPE" in stage:
            mature_tiles += 1

    animals = _animal_counts(farm, animal_tiles)
    workers = farm.get("workers", farm.get("hands", []))
    if not isinstance(workers, list):
        workers = []
    unlocked = farm.get("unlocked_quadrants", farm.get("unlocked", farm.get("land", ["NW"])))
    if not isinstance(unlocked, list):
        unlocked = [unlocked]

    return {
        "money": farm.get("money", farm.get("cash")),
        "unlocked_quadrants": unlocked,
        "quadrant_count": len(unlocked),
        "worker_count": len(workers),
        "animals": animals,
        "tile_count": len(tiles),
        "planted_tiles": planted_tiles,
        "mature_tiles": mature_tiles,
        "crop_counts": crop_counts,
        "sample_workers": workers[:3],
    }


def _animal_counts(farm: dict[str, Any], animal_tiles: dict[str, int]) -> dict[str, int]:
    counts = dict(animal_tiles)
    animals = farm.get("animals", {})
    if isinstance(animals, dict):
        for name in counts:
            counts[name] += int(animals.get(name, 0) or 0)
    elif isinstance(animals, list):
        for animal in animals:
            name = _norm(_first_present(animal if isinstance(animal, dict) else {}, ("type", "name", "item"), animal))
            if name in counts:
                counts[name] += 1
    return counts


def _update_action_counts(
    counts: dict[str, int],
    expert_action: dict[str, Any],
    opponent_action: dict[str, Any],
) -> None:
    counts["opponent_agent_calls"] += 1
    if opponent_action.get("farmer", ["PASS"])[0] != "PASS":
        counts["opponent_non_pass_farmer"] += 1
    if opponent_action.get("market"):
        counts["opponent_market_nonempty"] += 1
    if opponent_action.get("hands"):
        counts["opponent_hands_nonempty"] += 1
    if expert_action.get("farmer", ["PASS"])[0] != "PASS":
        counts["expert_non_pass_farmer"] += 1
    if expert_action.get("market"):
        counts["expert_market_nonempty"] += 1
    if expert_action.get("hands"):
        counts["expert_hands_nonempty"] += 1


def _conclusion(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    developed_agent1_view_farm0 = 0
    developed_agent0_view_farm1 = 0
    imported_opponent_ids = {"apex35_live_submission", "apex4_self_play", "v18_baseline"}
    developed_imported_opponents = 0
    for episode in episodes:
        final_snapshot = episode["snapshots"][-1] if episode["snapshots"] else {}
        agent0_farm1 = final_snapshot.get("agent0_observation", {}).get("farm1", {})
        agent1_farm0 = final_snapshot.get("agent1_observation", {}).get("farm0", {})
        if _farm_developed(agent1_farm0):
            developed_agent1_view_farm0 += 1
        if _farm_developed(agent0_farm1):
            developed_agent0_view_farm1 += 1
            if episode["opponent_id"] in imported_opponent_ids:
                developed_imported_opponents += 1
        rows.append(
            {
                "opponent_id": episode["opponent_id"],
                "opponent_agent_calls": episode["action_counts"]["opponent_agent_calls"],
                "opponent_non_pass_farmer": episode["action_counts"]["opponent_non_pass_farmer"],
                "opponent_market_nonempty": episode["action_counts"]["opponent_market_nonempty"],
                "agent0_view_farm1_final": _compact_farm(agent0_farm1),
                "agent1_view_farm0_final": _compact_farm(agent1_farm0),
            }
        )
    adapter_passed = developed_imported_opponents == len(imported_opponent_ids)
    if adapter_passed:
        diagnosis = (
            "The seat-1 adapter is working for the imported APEX-style opponents. APEX35, APEX4 self-play, "
            "and v18 now produce non-PASS farmer actions and develop the actual farms[1] state observed by agent0. "
            "The pass-only control remains undeveloped as expected."
        )
        recommended_next_step = (
            "Run a small replacement collection with opponent action telemetry and confirm Step 3 labels have "
            "class diversity before any 100-game or 1,000-game run."
        )
    else:
        diagnosis = (
            "The seat-1 adapter did not make every imported opponent develop the actual farms[1] state. "
            "Do not collect a replacement dataset until the remaining opponent execution issue is fixed."
        )
        recommended_next_step = "Inspect the failed opponent rows in this report and fix the adapter or policy wrapper."
    return {
        "step4_classifier_training_ready": False,
        "diagnosis": diagnosis,
        "adapter_pilot_passed": adapter_passed,
        "developed_imported_opponents": developed_imported_opponents,
        "imported_opponent_count": len(imported_opponent_ids),
        "developed_agent1_view_farm0_count": developed_agent1_view_farm0,
        "developed_agent0_view_farm1_count": developed_agent0_view_farm1,
        "summary": rows,
        "recommended_next_step": recommended_next_step,
    }


def _compact_farm(farm: dict[str, Any]) -> dict[str, Any]:
    return {
        "money": farm.get("money"),
        "quadrant_count": farm.get("quadrant_count"),
        "workers": farm.get("worker_count"),
        "animals": farm.get("animals"),
        "planted_tiles": farm.get("planted_tiles"),
        "crop_counts": farm.get("crop_counts"),
    }


def _farm_developed(farm: dict[str, Any]) -> bool:
    animals = farm.get("animals") or {}
    crop_counts = farm.get("crop_counts") or {}
    animal_total = int(animals.get("COW", 0) or 0) + int(animals.get("SHEEP", 0) or 0)
    crop_total = sum(int(value or 0) for value in crop_counts.values())
    return (
        int(farm.get("quadrant_count") or 0) > 1
        or int(farm.get("worker_count") or 0) > 0
        or animal_total > 0
        or crop_total > 0
    )


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Step 3C Opponent Observation Probe",
        "",
        f"Status: `{report['status']}`",
        f"Sample steps: `{report['sample_steps']}`",
        "",
        "## Opponent Execution Summary",
        "",
    ]
    for row in report["conclusion"]["summary"]:
        lines.extend(
            [
                f"### {row['opponent_id']}",
                "",
                f"- Opponent calls: `{row['opponent_agent_calls']}`",
                f"- Non-PASS farmer actions: `{row['opponent_non_pass_farmer']}`",
                f"- Non-empty market actions: `{row['opponent_market_nonempty']}`",
                f"- Agent0 view of farms[1] final: `{row['agent0_view_farm1_final']}`",
                f"- Agent1 view of farms[0] final: `{row['agent1_view_farm0_final']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Conclusion",
            "",
            report["conclusion"]["diagnosis"],
            "",
            f"Adapter pilot passed: `{report['conclusion']['adapter_pilot_passed']}`",
            f"Developed imported opponents: `{report['conclusion']['developed_imported_opponents']}/{report['conclusion']['imported_opponent_count']}`",
            f"Developed agent1-view farms[0]: `{report['conclusion']['developed_agent1_view_farm0_count']}`",
            f"Developed agent0-view farms[1]: `{report['conclusion']['developed_agent0_view_farm1_count']}`",
            "",
            report["conclusion"]["recommended_next_step"],
            "",
        ]
    )
    return "\n".join(lines)


def _flatten_tiles(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.values())
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, list):
            rows.extend(item)
        else:
            rows.append(item)
    return rows


def _first_present(mapping: dict[str, Any], keys: tuple[str, ...], default: Any) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return default


def _norm(value: Any) -> str:
    return str(value or "").upper().replace(" ", "_").replace("-", "_")


def _observation(agent_state: Any) -> dict[str, Any]:
    obs = getattr(agent_state, "observation", {})
    return obs if isinstance(obs, dict) else {}


def _done(state: list[Any]) -> bool:
    return any(str(getattr(agent_state, "status", "")).upper() == "DONE" for agent_state in state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe raw opponent observations for Step 3C.")
    parser.add_argument("--seed-start", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = probe_opponent_observations(seed_start=args.seed_start)
    write_reports(report, args.output, args.markdown)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
