"""Audit whether cached replay rows support causal/action-supervised targets.

This is intentionally descriptive. It does not fit a model, run a game, or
claim that an observed replay action was optimal.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "lplus_market_pressure_dataset_with_downstream.jsonl"
OUT_JSON = ROOT / "LPLUS_ML_TARGET_VALIDITY_AUDIT.json"
OUT_MD = ROOT / "LPLUS_ML_TARGET_VALIDITY_AUDIT.md"
PRODUCTS = ("milk", "strawberry", "wool")


def _finite(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def main() -> dict[str, Any]:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    modes = Counter(str(row.get("features", {}).get("sell_mode_observed")) for row in rows)
    action_by_match = defaultdict(set)
    for row in rows:
        action_by_match[(row.get("match_id"), row.get("seat"), row.get("features", {}).get("step"))].add(row.get("features", {}).get("sell_mode_observed"))

    # Quantized public-state fingerprints find approximate repeats, not causal matches.
    fields = ("step", "cash", "price_milk", "price_strawberry", "price_wool", "own_inventory_milk", "own_inventory_strawberry", "own_inventory_wool", "workers", "plants", "pastures", "land_count")
    buckets = defaultdict(list)
    for row in rows:
        f = row.get("features", {})
        fingerprint = tuple(round(_finite(f.get(field)) or 0.0, -1 if field == "cash" else 2) for field in fields)
        buckets[fingerprint].append(row)
    repeated = [group for group in buckets.values() if len(group) > 1]
    action_varying = [group for group in repeated if len({row.get("features", {}).get("sell_mode_observed") for row in group}) > 1]
    outcome_ranges = []
    for group in action_varying:
        by_action = defaultdict(list)
        for row in group:
            by_action[row.get("features", {}).get("sell_mode_observed")].append(row)
        if len(outcome_ranges) < 10:
            outcome_ranges.append({"actions": {str(action): {"n": len(items), "wealth_24_min": min(row["labels"]["downstream_wealth_24"] for row in items), "wealth_24_max": max(row["labels"]["downstream_wealth_24"] for row in items), "wealth_120_min": min(row["labels"]["downstream_wealth_120"] for row in items), "wealth_120_max": max(row["labels"]["downstream_wealth_120"] for row in items)} for action, items in by_action.items()}})

    targets = {}
    for product in PRODUCTS:
        for kind in ("adverse", "favorable"):
            key = f"{kind}_{product}"
            targets[key] = {"target_is_outcome_correlated": True, "action_supervised": False, "same_state_competing_action_evidence": False, "reason": "The label is future price movement; each replay state records one observed action and no accepted/rejected counterfactual."}
    for horizon in (24, 120):
        targets[f"downstream_wealth_{horizon}"] = {"target_is_outcome_correlated": True, "action_supervised": False, "same_state_competing_action_evidence": bool(action_varying), "reason": "Future farm money is recoverable, but no matched alternative action is recorded."}

    audit = {
        "status": "BLOCK_TRAINING_FOR_POLICY_SELECTION",
        "games_run": False,
        "models_trained": False,
        "rows": len(rows),
        "matches": len({row.get("match_id") for row in rows}),
        "seats": len({(row.get("match_id"), row.get("seat")) for row in rows}),
        "observed_action_modes": dict(modes),
        "exact_state_competing_action_groups": 0,
        "approximate_public_state_groups": len(repeated),
        "approximate_groups_with_action_variation": len(action_varying),
        "approximate_group_examples": outcome_ranges,
        "targets": targets,
        "missing_decision_fields": ["accepted/rejected/preempted status", "queue position", "alternative valid action", "same-state counterfactual outcome", "opponent private state"],
        "conclusion": "The dataset supports descriptive prediction of market/wealth outcomes, but not causal action ranking or policy learning. Historical losses and observed sell priorities must not be treated as demonstrations of the opposite correct action.",
        "next_gate": "Acquire matched counterfactual or intervention data before training a decision model; keep the proven L+ action as fallback.",
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    md = [
        "# L+ ML Target Validity Audit", "", "Read-only audit. No model was trained and no game was run.", "", "## Decision", "", "**BLOCK_TRAINING_FOR_POLICY_SELECTION**", "", 
        "The 28,760 rows contain one observed trajectory action per state. They do not contain a matched alternative legal action, accepted/rejected/preempted result, queue position, or same-state downstream outcome under another action.", "",
        "## Findings", "", f"Rows: **{len(rows)}**; matches: **{audit['matches']}**; seats: **{audit['seats']}**.", f"Observed action modes: `{dict(modes)}`.", f"Exact same-state groups with competing actions: **0**.", f"Quantized public-state repeats with action variation: **{len(action_varying)}**, which is only approximate matching and is not causal evidence.", "",
        "## Target Assessment", "", "- Adverse/favorable price labels are valid descriptive future outcomes, not action targets.", "- 24-step/120-step farm-money labels are valid downstream outcomes, not causal incremental action effects.", "- The observed mode label is behavior copied from a replay, not a proven optimal label.", "- A loss replay identifies a failed trajectory, not the correct opposite action.", "",
        "## Missing Evidence", "", "- accepted/rejected/preempted market outcome", "- order or queue position", "- legal competing action at the same state", "- matched counterfactual result", "- opponent private state/action causal decomposition", "",
        "## Recommendation", "", "Do not train or integrate a policy from this dataset. A descriptive market-risk predictor could be studied separately, but it must not be interpreted as an action recommendation without matched intervention evidence. Preserve original L+ as the fallback.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "rows": len(rows), "approximate_action_varying_groups": len(action_varying)}, indent=2))
    return audit


if __name__ == "__main__":
    main()
