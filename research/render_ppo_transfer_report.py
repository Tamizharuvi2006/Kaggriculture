"""Render the already-produced PPO transfer JSON without recomputing probes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / "ppo_transfer_value_market_labels.json").read_text(encoding="utf-8"))
lines = [
    "# Frozen PPO Transfer-Value Audit",
    "",
    "Scope: read-only offline probes against cached replay labels. No games or PPO fine-tuning were run.",
    "",
    f"Status: **{source['status']}**",
    f"Rows enriched from raw replays: **{source['enriched_rows']}/{source['dataset_rows']}**",
    "",
    "The frozen selector has 133 inputs, a 32-unit shared hidden representation, and four outputs: `u_market`, `u_route`, confidence, and value.",
    "",
    "Probe AUC is validation-only. `ppo_hidden32` tests the frozen representation, `ppo_outputs4` tests frozen outputs, and `price_trend_baseline` uses current price plus 1/3/6-step trends.",
    "",
]
for scope_name, scope in source["evaluation"].items():
    lines.extend([f"## {scope_name}", "", f"Train rows: {scope['train_rows']}; validation rows: {scope['validation_rows']}.", "", "| Target | PPO hidden | PPO outputs | Price/trend |", "|---|---:|---:|---:|"])
    for target, result in scope["targets"].items():
        if result.get("status") != "PASS":
            lines.append(f"| {target} | n/a | n/a | n/a |")
            continue
        probes = result["probes"]
        values = [probes[name]["auc"] for name in ("ppo_hidden32", "ppo_outputs4", "price_trend_baseline")]
        formatted = ["n/a" if value is None else f"{value:.3f}" for value in values]
        lines.append(f"| {target} | {formatted[0]} | {formatted[1]} | {formatted[2]} |")
    lines.append("")
lines.extend([
    "## Conclusion",
    "",
    "The frozen representation shows mixed predictive transfer and no consistent advantage over simple price/trend features. The step-120 slice has only 32 train and 8 validation rows with single-class validation labels, so it cannot support a transfer claim.",
    "",
    "Recommendation: do not reuse the PPO representation as the default market model. Prefer a fresh small supervised market model if later label-quality work justifies training. This audit is predictive only, not causal evidence.",
])
(ROOT / "PPO_TRANSFER_VALUE_MARKET_LABELS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
