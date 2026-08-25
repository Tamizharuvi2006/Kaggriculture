"""Audit v18 decision opportunities from the existing real-game trace cache."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def audit(input_path: Path, output_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = [row for result in payload["results"] for row in result["rows"]]
    event_counts = Counter()
    event_steps = defaultdict(Counter)
    cooccurrence = Counter()
    coverage = defaultdict(set)
    for row in rows:
        orders = [order for order in row["candidate_action"].get("market", []) if order]
        kinds = {str(order[0]) for order in orders}
        for order in orders:
            key = ":".join(str(value) for value in order[:2])
            event_counts[key] += 1
            event_steps[key][row["step"]] += 1
            coverage[key].add((row["step"], row["candidate_state_before"].get("money")))
        for left in sorted(kinds):
            for right in sorted(kinds):
                if left < right:
                    cooccurrence[f"{left}+{right}"] += 1
    opportunities = [
        {
            "opportunity": "livestock_preference",
            "baseline_action": "BUY_ANIMAL COW",
            "alternative": "retain v18 order set but prioritize an existing BUY_ANIMAL COW before another investment",
            "coverage_events": event_counts["BUY_ANIMAL:COW"],
            "coverage_games": len({idx for idx, result in enumerate(payload["results"]) if any("BUY_ANIMAL" in str(row["candidate_action"]) for row in result["rows"])}),
            "safety_requirement": "only reorder an existing affordable v18 order; never inject a purchase",
        },
        {
            "opportunity": "premium_crop_preference",
            "baseline_action": "BUY_SEED STRAWBERRY",
            "alternative": "retain v18 order set but prioritize an existing BUY_SEED STRAWBERRY before another investment",
            "coverage_events": event_counts["BUY_SEED:STRAWBERRY"],
            "coverage_games": len({idx for idx, result in enumerate(payload["results"]) if any("STRAWBERRY" in str(row["candidate_action"]) for row in result["rows"])}),
            "safety_requirement": "only reorder an existing affordable v18 order; preserve all sells and quantities",
        },
        {
            "opportunity": "wheat_preference",
            "baseline_action": "BUY_PRODUCT WHEAT / BUY_SEED WHEAT",
            "alternative": "only reorder an existing wheat investment; do not change quantity or add orders",
            "coverage_events": event_counts["BUY_PRODUCT:WHEAT"] + event_counts["BUY_SEED:WHEAT"],
            "coverage_games": len({idx for idx, result in enumerate(payload["results"]) if any("WHEAT" in str(row["candidate_action"]) for row in result["rows"])}),
            "safety_requirement": "must not displace v18 sell/liquidity orders",
        },
        {
            "opportunity": "hire_tradeoff",
            "baseline_action": "HIRE",
            "alternative": "do not replace; only study as a control because it drives v18 progression",
            "coverage_events": event_counts["HIRE"],
            "coverage_games": len(payload["results"]),
            "safety_requirement": "not a safe first modifier; worker progression is a v18 invariant",
        },
    ]
    report = {
        "status": "PASS",
        "diagnostic": "cached fixed-v18 decision opportunity audit",
        "input": str(input_path),
        "episodes": len(payload["results"]),
        "transitions": len(rows),
        "event_counts": dict(event_counts),
        "event_step_histograms": {key: dict(sorted(value.items())) for key, value in event_steps.items()},
        "cooccurring_action_kinds": dict(cooccurrence),
        "opportunities": opportunities,
        "recommendation": "Do not modify v18 yet. The first candidate should be an existing-order livestock or premium preference, gated by actual order presence and liquidity preservation.",
        "code_modified": False,
        "ppo_started": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("reports/step5b/apex4_kaggle_entrypoint_diagnostic.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/v18_decision_opportunity_audit.json"))
    args = parser.parse_args()
    report = audit(args.input, args.output)
    print(json.dumps({"status": report["status"], "transitions": report["transitions"], "event_counts": report["event_counts"], "opportunities": report["opportunities"]}, indent=2))


if __name__ == "__main__":
    main()
