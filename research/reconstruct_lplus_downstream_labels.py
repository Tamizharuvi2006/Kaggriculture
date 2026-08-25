"""Reconstruct downstream wealth labels from cached full Kaggriculture replays.

Read-only research utility. It does not import kaggle_environments, run games,
or modify any competition/model artifact. The reconstruction intentionally
matches the historical mcv replay parser: future farm money is read directly
from the cached observation at step+24 and step+120.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "reports" / "step5b" / "old_loss_gauntlet" / "raw_replays"
SOURCE = ROOT / "lplus_market_pressure_dataset.jsonl"
OUTPUT = ROOT / "lplus_market_pressure_dataset_with_downstream.jsonl"
AUDIT_JSON = ROOT / "LPLUS_ML_DOWNSTREAM_LABEL_AUDIT.json"
AUDIT_MD = ROOT / "LPLUS_ML_DOWNSTREAM_LABEL_AUDIT.md"
HORIZON = 720


def _match_id(value: str) -> str:
    return value.replace("episode-", "").replace("-replay", "").replace(".json", "")


def _money_at(replay: dict[str, Any], seat: int, step: int) -> float | None:
    steps = replay.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    idx = min(max(0, step), HORIZON - 1, len(steps) - 1)
    row = steps[idx]
    if not isinstance(row, list) or seat >= len(row):
        return None
    record = row[seat]
    observation = record.get("observation") if isinstance(record, dict) else None
    farms = observation.get("farms") if isinstance(observation, dict) else None
    farm = farms[seat] if isinstance(farms, list) and seat < len(farms) else None
    if not isinstance(farm, dict):
        return None
    value = farm.get("money", farm.get("cash"))
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _load_replays() -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(RAW_ROOT.glob("*/episode-*-replay.json")):
        try:
            replay = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        steps = replay.get("steps")
        config = replay.get("configuration") or {}
        if isinstance(steps, list) and len(steps) >= HORIZON and int(config.get("episodeSteps", HORIZON)) == HORIZON:
            result[_match_id(path.name)] = (path, replay)
    return result


def build() -> dict[str, Any]:
    replays = _load_replays()
    rows = 0
    joined = 0
    missing_replay = Counter()
    missing_24 = 0
    missing_120 = 0
    bad_rows = 0
    validation_examples: list[dict[str, Any]] = []

    with SOURCE.open("r", encoding="utf-8") as source, OUTPUT.open("w", encoding="utf-8", newline="\n") as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            rows += 1
            match_id = str(row.get("match_id", ""))
            seat = row.get("seat")
            step = row.get("features", {}).get("step")
            item = replays.get(match_id)
            if item is None or not isinstance(seat, int) or not isinstance(step, int):
                missing_replay[match_id] += 1
                bad_rows += 1
                target.write(json.dumps(row, separators=(",", ":")) + "\n")
                continue
            _, replay = item
            wealth_24 = _money_at(replay, seat, step + 24)
            wealth_120 = _money_at(replay, seat, step + 120)
            labels = row.setdefault("labels", {})
            labels["downstream_wealth_24"] = wealth_24
            labels["downstream_wealth_120"] = wealth_120
            current_cash = row.get("features", {}).get("cash")
            labels["downstream_cash_delta_24"] = wealth_24 - current_cash if wealth_24 is not None and isinstance(current_cash, (int, float)) else None
            labels["downstream_cash_delta_120"] = wealth_120 - current_cash if wealth_120 is not None and isinstance(current_cash, (int, float)) else None
            joined += 1
            missing_24 += wealth_24 is None
            missing_120 += wealth_120 is None
            if len(validation_examples) < 5:
                validation_examples.append({"match_id": match_id, "seat": seat, "step": step, "wealth_24": wealth_24, "wealth_120": wealth_120})
            target.write(json.dumps(row, separators=(",", ":")) + "\n")

    audit = {
        "status": "PASS" if rows and joined == rows and not missing_24 and not missing_120 else "FAIL",
        "scope": "offline cached replay reconstruction only",
        "games_run": False,
        "training_run": False,
        "source_dataset": str(SOURCE.relative_to(ROOT)),
        "output_dataset": str(OUTPUT.relative_to(ROOT)),
        "raw_replay_root": str(RAW_ROOT.relative_to(ROOT)),
        "raw_replays_loaded": len(replays),
        "source_rows": rows,
        "rows_joined": joined,
        "rows_missing_replay": sum(missing_replay.values()),
        "rows_missing_wealth_24": missing_24,
        "rows_missing_wealth_120": missing_120,
        "bad_rows": bad_rows,
        "reconstruction_rule": {
            "wealth_24": "steps[min(719, step + 24)][seat].observation.farms[seat].money",
            "wealth_120": "steps[min(719, step + 120)][seat].observation.farms[seat].money",
            "source": "same direct-observation rule used by research/build_mcv_replay_dataset.py",
        },
        "validation_examples": validation_examples,
        "id_join_note": "The older data/replay/mcv_replay_dataset.json has zero ID overlap with these 20 raw replays; labels are reconstructed from the matching full raw trajectories instead.",
        "limitations": [
            "Farm money is a downstream wealth proxy, not causal incremental MCV.",
            "Raw replays do not expose native accepted/rejected/preempted market outcomes.",
            "The historical replay policy is not guaranteed to be L+ in every source match.",
        ],
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    md = [
        "# L+ ML Downstream Label Audit", "", "Scope: read-only reconstruction from cached complete raw replays. No games or training were run.", "",
        f"Status: **{audit['status']}**", f"Loaded raw replays: **{len(replays)}**", f"Source rows: **{rows}**", f"Rows joined: **{joined}**", "",
        "## Reconstruction", "",
        "The labels use the existing parser rule exactly: `steps[min(719, step + offset)][seat].observation.farms[seat].money`, with offsets 24 and 120. No future prices, terminal MCV, or invented values are used as features.", "",
        "## Validation", "",
        f"Missing 24-step values: **{missing_24}**; missing 120-step values: **{missing_120}**; unmatched rows: **{sum(missing_replay.values())}**.",
        "The historical reduced MCV dataset has zero replay-ID overlap with the 20 current raw trajectories, so the clean join is performed against the full matching raw files.", "",
        "## Boundary", "",
        "This proves recoverability of downstream farm-money labels for offline modeling. It does not prove causal market impact, accepted/rejected order outcomes, or that the observed policy is L+.", "",
        "## Artifacts", "", f"- `{OUTPUT.relative_to(ROOT)}`", f"- `{AUDIT_JSON.relative_to(ROOT)}`", "- Original dataset preserved unchanged.",
    ]
    AUDIT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
