"""Read-only context audit for high-impact v18 decisions in cached traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from v18_high_impact_cached_audit import iter_json_array


def numeric_state(state: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for key in ("money", "workers", "land"):
        value = state.get(key)
        if isinstance(value, (int, float)):
            values[key] = float(value)
    for key in ("animals", "hands", "tiles"):
        value = state.get(key)
        if isinstance(value, (list, dict)):
            values[f"{key}_size"] = float(len(value))
    return values


def movement(before: dict[str, float], after: dict[str, float]) -> float:
    return sum(abs(after.get(key, value) - value) for key, value in before.items())


def money_bin(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    if value < 1000:
        return "<1000"
    if value < 3000:
        return "1000-2999"
    if value < 6000:
        return "3000-5999"
    return ">=6000"


def audit(input_path: Path, output_path: Path) -> dict[str, Any]:
    target_counts = Counter()
    context_counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    impact_totals: Counter[str] = Counter()
    impact_counts: Counter[str] = Counter()
    episodes = transitions = 0

    for result in iter_json_array(input_path, "results"):
        episodes += 1
        rows = result.get("rows", [])
        transitions += len(rows)
        for index, row in enumerate(rows):
            action = row.get("candidate_action", {})
            market = action.get("market", []) if isinstance(action, dict) else []
            orders = [order for order in market if order]
            keys = [": ".join(str(value) for value in order[:2]) for order in orders]
            state = row.get("candidate_state_before", {})
            before = numeric_state(state)
            alternatives = sorted({key for key in keys if key not in {"HIRE", "BUY_PRODUCT: WHEAT"}})
            for target in ("HIRE", "BUY_PRODUCT: WHEAT"):
                if target not in keys:
                    continue
                target_counts[target] += 1
                context = f"{target} | cash={money_bin(state.get('money'))} | alternatives={','.join(alternatives) or 'none'}"
                context_counts[target][context] += 1
                horizons: dict[str, float] = {}
                for horizon in (24, 72, 168, 719):
                    future = rows[min(index + horizon, len(rows) - 1)].get("candidate_state_before", {})
                    impact = movement(before, numeric_state(future))
                    horizons[f"h{horizon}"] = round(impact, 3)
                    impact_totals[f"{target}:{horizon}"] += impact
                    impact_counts[f"{target}:{horizon}"] += 1
                if len(examples[target]) < 12:
                    examples[target].append({
                        "episode_index": episodes - 1,
                        "step": row.get("step", index),
                        "pre_action_state": state,
                        "actual_v18_orders": orders,
                        "observed_cooccurring_orders": alternatives,
                        "downstream_state_movement": horizons,
                        "counterfactual_limit": "No alternative outcome/reward is stored; this is context evidence, not a causal counterfactual result.",
                    })

    contexts = {}
    for target, counts in context_counts.items():
        contexts[target] = [
            {"context": context, "events": count}
            for context, count in counts.most_common(20)
        ]
    opportunities = []
    for target, count in target_counts.items():
        avg_terminal = impact_totals[f"{target}:719"] / max(1, impact_counts[f"{target}:719"])
        if target == "HIRE":
            safety = "High impact but worker progression is a v18 invariant; study only, do not replace yet."
        else:
            safety = "High impact but liquidity/town-consumption coupled; only study quantity/timing when cash and sell safeguards remain unchanged."
        opportunities.append({
            "decision": target,
            "events": count,
            "mean_observed_terminal_state_movement": round(avg_terminal, 3),
            "safety_assessment": safety,
            "rank": 1 if target == "BUY_PRODUCT: WHEAT" else 2,
        })
    opportunities.sort(key=lambda item: item["rank"])
    report = {
        "status": "PASS",
        "diagnostic": "cached fixed-v18 HIRE and BUY_PRODUCT WHEAT decision-context audit",
        "input": str(input_path),
        "episodes": episodes,
        "transitions": transitions,
        "target_counts": dict(target_counts),
        "ranked_opportunities": opportunities,
        "context_rankings": contexts,
        "representative_examples": examples,
        "interpretation": "Existing traces show observed downstream movement, not counterfactual reward differences. No alternative action was executed.",
        "games_executed": 0,
        "code_behavior_modified": False,
        "ppo_started": False,
        "recommendation": "Do not implement HIRE changes. For BUY_PRODUCT WHEAT, only a cached-context rule preserving sells, affordability, and liquidity could be considered next; a true candidate still needs a single controlled game validation.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("reports/step5b/apex4_kaggle_entrypoint_diagnostic.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/v18_cached_counterfactual_audit.json"))
    args = parser.parse_args()
    report = audit(args.input, args.output)
    print(json.dumps({"status": report["status"], "episodes": report["episodes"], "transitions": report["transitions"], "target_counts": report["target_counts"], "ranked_opportunities": report["ranked_opportunities"], "recommendation": report["recommendation"]}, indent=2))


if __name__ == "__main__":
    main()
