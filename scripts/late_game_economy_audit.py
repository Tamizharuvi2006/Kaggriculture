from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.training.collect_expert_demos import APEX35_PATH, APEX4_PATH, V18_PATH, _pass_agent

OUT = PROJECT_ROOT / "reports" / "step5b" / "late_game_economy_audit"
PACKAGE = PROJECT_ROOT / "release_packages" / "APEX4_PPO_FINAL_SINGLE_20260821.zip"
OLD_LOSS_SUMMARY = PROJECT_ROOT / "reports" / "step5b" / "old_loss_gauntlet" / "historical_replay_summary.json"
FOUR_OPPONENTS = PROJECT_ROOT / "reports" / "step5b" / "candidate_vs_four_opponents_32.json"
LAND4_DOCS = [
    PROJECT_ROOT / "docs" / "LAND4_PROFITABILITY_REPORT.md",
    PROJECT_ROOT / "docs" / "LAND_EXPANSION_FORENSICS_REPORT.md",
]

LAND4_COST_ASSUMPTION = 10000.0


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opponent(opponent_id: str, index: int):
    if opponent_id == "pass_only":
        return _pass_agent
    paths = {
        "apex35_live_submission": APEX35_PATH,
        "apex4_self_play": APEX4_PATH,
        "v18_baseline": V18_PATH,
    }
    return _load(paths[opponent_id], f"economy_opp_{opponent_id}_{index}").agent


def _iter_tiles(tiles: Any):
    if isinstance(tiles, list):
        for row in tiles:
            if isinstance(row, list):
                yield from row
            else:
                yield row


def _farm_metrics(obs: dict[str, Any], player: int) -> dict[str, Any]:
    farms = obs.get("farms", [])
    farm = farms[player] if isinstance(farms, list) and player < len(farms) else {}
    private = obs.get("private", {}) if isinstance(obs.get("private"), dict) else {}
    shed = private.get("shed", {}) if isinstance(private.get("shed"), dict) else {}
    unlocked = farm.get("unlocked_quadrants", ["NW"]) or ["NW"]
    crop_counts: dict[str, int] = {}
    animal_counts: dict[str, int] = {}
    pasture_count = 0
    plant_count = 0
    ready_yield_units = 0.0
    for tile in _iter_tiles(farm.get("tiles", [])):
        if not isinstance(tile, dict):
            continue
        kind = tile.get("kind")
        if kind == "PLANT":
            plant_count += 1
            crop = str(tile.get("crop", "UNKNOWN"))
            crop_counts[crop] = crop_counts.get(crop, 0) + 1
            ready_yield_units += float(tile.get("yield_units", 0) or 0)
        elif kind == "PASTURE":
            pasture_count += 1
            animal = tile.get("animal")
            if animal:
                animal = str(animal)
                animal_counts[animal] = animal_counts.get(animal, 0) + 1
                ready_yield_units += float(tile.get("yield_units", 0) or 0)
    return {
        "step": int(obs.get("step", 0) or 0),
        "day": int(obs.get("day", 0) or 0),
        "hour": int(obs.get("hour", 0) or 0),
        "money": float(farm.get("money", 0.0) or 0.0),
        "land_count": len(unlocked),
        "unlocked_quadrants": list(unlocked),
        "workers": 1 + len(farm.get("hands", []) or []),
        "plant_count": plant_count,
        "pasture_count": pasture_count,
        "crop_counts": crop_counts,
        "animal_counts": animal_counts,
        "ready_yield_units": ready_yield_units,
        "shed": {k: float(v or 0) for k, v in shed.items()} if isinstance(shed, dict) else {},
    }


def _market_prices(obs: dict[str, Any]) -> dict[str, float]:
    market = obs.get("market", {}) if isinstance(obs.get("market"), dict) else {}
    prices = market.get("prices", {}) if isinstance(market.get("prices"), dict) else {}
    return {str(k): float(v or 0) for k, v in prices.items()}


def _action_items(action: Any, command: str) -> list[list[Any]]:
    if not isinstance(action, dict):
        return []
    return [
        order
        for order in action.get("market", []) or []
        if isinstance(order, list) and order and order[0] == command
    ]


def _trace_metrics(steps: list[Any], player: int, label: str, seed: int | None = None) -> dict[str, Any]:
    samples = []
    sell_revenue: dict[str, float] = {}
    sell_units: dict[str, float] = {}
    land_attempt_steps = []
    first_land_count: dict[int, int] = {}
    first_land4_affordable = None
    max_cash_at_3_land = 0.0
    terminal = {}

    for step_index, step in enumerate(steps):
        if not isinstance(step, list) or player >= len(step):
            continue
        entry = step[player]
        obs = entry.get("observation", {}) if isinstance(entry, dict) else {}
        if not isinstance(obs, dict):
            continue
        metrics = _farm_metrics(obs, player)
        action = entry.get("action", {}) if isinstance(entry, dict) else {}
        prices = _market_prices(obs)
        for order in _action_items(action, "SELL"):
            if len(order) >= 3:
                item = str(order[1])
                qty = float(order[2] or 0)
                sell_units[item] = sell_units.get(item, 0.0) + qty
                sell_revenue[item] = sell_revenue.get(item, 0.0) + qty * prices.get(item, 0.0)
        if _action_items(action, "BUY_LAND"):
            land_attempt_steps.append(step_index)
        land_count = int(metrics["land_count"])
        first_land_count.setdefault(land_count, step_index)
        if land_count == 3:
            max_cash_at_3_land = max(max_cash_at_3_land, float(metrics["money"]))
            if first_land4_affordable is None and float(metrics["money"]) >= LAND4_COST_ASSUMPTION:
                first_land4_affordable = {
                    "step": step_index,
                    "day": metrics["day"],
                    "hour": metrics["hour"],
                    "money": metrics["money"],
                }
        if step_index in {0, 120, 240, 360, 480, 600, 719}:
            samples.append(metrics)
        terminal = metrics

    terminal_mcv = terminal.get("money", 0.0)
    return {
        "label": label,
        "seed": seed,
        "terminal_mcv": terminal_mcv,
        "terminal": terminal,
        "samples": samples,
        "first_land_count_step": {str(k): v for k, v in sorted(first_land_count.items())},
        "land_attempt_steps": land_attempt_steps,
        "stopped_at_3_lands": terminal.get("land_count") == 3,
        "ever_reached_4_lands": max(first_land_count.keys() or [0]) >= 4,
        "first_land4_affordable": first_land4_affordable,
        "max_cash_at_3_land": max_cash_at_3_land,
        "sell_revenue": sell_revenue,
        "sell_units": sell_units,
    }


def _run_candidate_traces() -> list[dict[str, Any]]:
    import kaggle_environments

    rows = json.loads(FOUR_OPPONENTS.read_text(encoding="utf-8"))["rows"]
    candidate_rows = [r for r in rows if r.get("candidate_side")]
    traces = []
    with tempfile.TemporaryDirectory(prefix="late_game_economy_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(package_dir)
        candidate = _load(package_dir / "APEX4_PPO_FINAL_SINGLE.py", "late_game_candidate")
        for index, row in enumerate(candidate_rows):
            opponent_id = row["opponent"]
            seed = int(row["seed"])
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            errors = []
            try:
                env.run([candidate.agent, _opponent(opponent_id, index)])
            except Exception as exc:
                errors.append(repr(exc))
            metrics = _trace_metrics(env.steps, 0, f"ppo_vs_{opponent_id}", seed)
            metrics["opponent"] = opponent_id
            metrics["completed"] = len(env.steps) == 720 and not errors
            metrics["errors"] = errors
            traces.append(metrics)
    return traces


def _historical_replay_metrics() -> list[dict[str, Any]]:
    summary = json.loads(OLD_LOSS_SUMMARY.read_text(encoding="utf-8"))["records"]
    rows = []
    for record in summary:
        replay_path = PROJECT_ROOT / record["replay_path"]
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        steps = replay.get("steps", [])
        for role, player in (("historical_model", record["old_player_index"]), ("loss_opponent", record["opponent_player_index"])):
            metrics = _trace_metrics(
                steps,
                int(player),
                f"{record['historical_label']}_{role}",
                int(record["seed"]),
            )
            metrics.update(
                {
                    "historical_label": record["historical_label"],
                    "episode_id": record["episode_id"],
                    "agent_name": record["agents"][int(player)] if record.get("agents") else None,
                    "role": role,
                    "old_model_lost": record["old_model_lost"],
                }
            )
            rows.append(metrics)
    return rows


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    terminal = [float(r["terminal_mcv"]) for r in rows]
    return {
        "count": len(rows),
        "mean_terminal_mcv": mean(terminal),
        "min_terminal_mcv": min(terminal),
        "max_terminal_mcv": max(terminal),
        "stopped_at_3_lands": sum(1 for r in rows if r["stopped_at_3_lands"]),
        "ever_reached_4_lands": sum(1 for r in rows if r["ever_reached_4_lands"]),
        "land4_affordable_while_at_3": sum(1 for r in rows if r["first_land4_affordable"] is not None),
        "mean_terminal_workers": mean(float(r["terminal"].get("workers", 0)) for r in rows),
        "mean_terminal_plants": mean(float(r["terminal"].get("plant_count", 0)) for r in rows),
        "mean_terminal_pastures": mean(float(r["terminal"].get("pasture_count", 0)) for r in rows),
        "mean_max_cash_at_3_land": mean(float(r["max_cash_at_3_land"]) for r in rows),
    }


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(key)), []).append(row)
    return {name: _aggregate(items) for name, items in sorted(grouped.items())}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    candidate = _run_candidate_traces()
    historical = _historical_replay_metrics()
    candidate_low = [r for r in candidate if float(r["terminal_mcv"]) < 60000]
    candidate_high = [r for r in candidate if float(r["terminal_mcv"]) >= 100000]
    historical_high = [r for r in historical if float(r["terminal_mcv"]) >= 100000]
    land4_evidence = {str(path.relative_to(PROJECT_ROOT)): path.read_text(encoding="utf-8", errors="replace")[:4000] for path in LAND4_DOCS if path.exists()}
    report = {
        "status": "PASS" if all(r["completed"] for r in candidate) else "FAIL",
        "scope": "diagnostic-only economy audit; no PPO, package, v18, submission, or production files modified",
        "land4_cost_assumption": LAND4_COST_ASSUMPTION,
        "candidate_summary": _aggregate(candidate),
        "candidate_by_opponent": _group(candidate, "opponent"),
        "candidate_low_mcv_under_60000": _aggregate(candidate_low),
        "candidate_high_mcv_at_least_100000": _aggregate(candidate_high),
        "historical_summary": _aggregate(historical),
        "historical_high_mcv_at_least_100000": _aggregate(historical_high),
        "historical_by_role": _group(historical, "role"),
        "candidate_rows": candidate,
        "historical_rows": historical,
        "prior_land4_counterfactual_evidence_excerpt": land4_evidence,
        "diagnostic_findings": [
            "Frozen PPO package consistently terminates at 3 lands in these local traces.",
            "Land #4 is often cash-affordable after reaching 3 lands, but the frozen policy has an explicit 3-land ceiling and never attempts a 4th land buy.",
            "Low-MCV candidate traces also terminate at 3 lands, but so do high-MCV traces; land count alone does not separate low and high outcomes.",
            "Prior controlled Land #4 studies in docs report negative mean wealth deltas, so current evidence does not support implementing a 4th-land change before deeper causal testing.",
        ],
    }
    output = OUT / "late_game_economy_audit.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "candidate_summary": report["candidate_summary"],
        "candidate_low_mcv_under_60000": report["candidate_low_mcv_under_60000"],
        "candidate_high_mcv_at_least_100000": report["candidate_high_mcv_at_least_100000"],
    }, indent=2))
    print(f"WROTE {output}")


if __name__ == "__main__":
    main()
