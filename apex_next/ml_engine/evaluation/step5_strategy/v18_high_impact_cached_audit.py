"""Rank fixed-v18 decision opportunities using the existing trace cache only.

The cache is large, so episodes are streamed from the JSON array instead of
loading the full report into memory. No Kaggriculture games are executed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator


def iter_json_array(path: Path, key: str) -> Iterator[dict[str, Any]]:
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as handle:
        buffer = ""
        found = False
        while True:
            chunk = handle.read(1024 * 1024)
            if chunk:
                buffer += chunk
            elif not buffer:
                break
            if not found:
                marker = buffer.find(f'"{key}"')
                if marker < 0:
                    if chunk:
                        buffer = buffer[-len(key) - 4 :]
                        continue
                    raise ValueError(f"missing JSON key: {key}")
                start = buffer.find("[", marker)
                if start < 0:
                    continue
                buffer = buffer[start + 1 :]
                found = True
            while True:
                buffer = buffer.lstrip()
                if buffer.startswith("]"):
                    return
                if not buffer:
                    break
                try:
                    item, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                yield item
                buffer = buffer[end:]
                if buffer.startswith(","):
                    buffer = buffer[1:]


def state_signature(state: dict[str, Any]) -> dict[str, float]:
    """Extract stable numeric economic fields for impact comparison."""
    result: dict[str, float] = {}
    for key in ("money", "workers", "land", "mcv", "score"):
        value = state.get(key)
        if isinstance(value, (int, float)):
            result[key] = float(value)
    farms = state.get("farms")
    if isinstance(farms, list) and farms:
        own = farms[0] if isinstance(farms[0], dict) else {}
        for key in ("money", "workers", "land", "mcv", "score"):
            value = own.get(key)
            if isinstance(value, (int, float)):
                result[f"farm0.{key}"] = float(value)
    return result


def distance(left: dict[str, float], right: dict[str, float]) -> float:
    return sum(abs(right.get(key, value) - value) for key, value in left.items())


def action_keys(row: dict[str, Any]) -> list[str]:
    action = row.get("candidate_action", {})
    market = action.get("market", []) if isinstance(action, dict) else []
    keys = []
    for order in market:
        if order:
            keys.append(": ".join(str(value) for value in order[:2]))
    if action.get("farmers") if isinstance(action, dict) else False:
        keys.append("FARMERS")
    return keys


def audit(input_path: Path, output_path: Path) -> dict[str, Any]:
    counters = Counter()
    step_histograms: dict[str, Counter[int]] = defaultdict(Counter)
    horizon_impact: dict[str, Counter[str]] = defaultdict(Counter)
    episodes = transitions = 0

    for result in iter_json_array(input_path, "results"):
        episodes += 1
        rows = result.get("rows", [])
        transitions += len(rows)
        for index, row in enumerate(rows):
            keys = action_keys(row)
            if not keys:
                continue
            state = row.get("candidate_state_before", {})
            baseline = state_signature(state)
            for key in keys:
                counters[key] += 1
                step = int(row.get("step", index))
                step_histograms[key][step] += 1
                for horizon in (24, 72, 168, 719):
                    target = rows[min(index + horizon, len(rows) - 1)].get("candidate_state_before", {})
                    impact = distance(baseline, state_signature(target))
                    bucket = "high" if impact >= 100 else "medium" if impact >= 10 else "low"
                    horizon_impact[key][f"h{horizon}.{bucket}"] += 1

    ranked = []
    for key, count in counters.most_common():
        relevant = {name: value for name, value in horizon_impact[key].items()}
        long_horizon = sum(value for name, value in relevant.items() if name.startswith("h719.") and not name.endswith("low"))
        ranked.append({
            "decision": key,
            "frequency": count,
            "frequency_per_transition": count / transitions if transitions else 0.0,
            "step_min": min(step_histograms[key]),
            "step_max": max(step_histograms[key]),
            "step_mode": step_histograms[key].most_common(1)[0][0],
            "downstream_impact_buckets": relevant,
            "long_horizon_nontrivial_count": long_horizon,
            "safety_note": "study only; any future modifier must preserve existing v18 order set, affordability, liquidity, sells, and quantities",
        })
    ranked.sort(key=lambda item: (item["long_horizon_nontrivial_count"], item["frequency"]), reverse=True)
    report = {
        "status": "PASS",
        "diagnostic": "cached fixed-v18 high-impact decision audit",
        "input": str(input_path),
        "episodes": episodes,
        "transitions": transitions,
        "ranked_decisions": ranked,
        "code_modified": False,
        "games_executed": 0,
        "ppo_started": False,
        "recommendation": "Select the highest-ranked decision only after reviewing its safety coupling; do not run a candidate from frequency alone.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("reports/step5b/apex4_kaggle_entrypoint_diagnostic.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/v18_high_impact_cached_audit.json"))
    args = parser.parse_args()
    report = audit(args.input, args.output)
    print(json.dumps({"status": report["status"], "episodes": report["episodes"], "transitions": report["transitions"], "ranked_decisions": report["ranked_decisions"]}, indent=2))


if __name__ == "__main__":
    main()
