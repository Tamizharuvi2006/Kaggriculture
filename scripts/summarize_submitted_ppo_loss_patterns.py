from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ANALYSIS = Path("reports/step5b/old_loss_gauntlet/submitted_ppo_loss_analysis.json")
data = json.loads(ANALYSIS.read_text(encoding="utf-8"))


def json_text(value) -> str:
    return json.dumps(value, sort_keys=True).upper()


def summarize(record):
    replay = json.loads(Path(record["replay_path"]).read_text(encoding="utf-8"))
    p = record["ppo_index"]
    steps = replay.get("steps", [])
    actions = [frame[p].get("action", {}) for frame in steps if len(frame) > p]
    market_counts = Counter()
    farmer_counts = Counter()
    sale_steps = {product: [] for product in ("MILK", "STRAWBERRY", "WOOL")}
    for idx, action in enumerate(actions):
        for item in action.get("market", []) if isinstance(action, dict) else []:
            text = json_text(item)
            for product in sale_steps:
                if product in text and "SELL" in text:
                    sale_steps[product].append(idx)
            match = re.search(r"(?:BUY|SELL)_[A-Z_]+", text)
            if match:
                market_counts[match.group(0)] += 1
        for item in action.get("farmer", []) if isinstance(action, dict) else []:
            farmer_counts[str(item)] += 1
    final = steps[-1] if steps else []
    farm = final[p].get("observation", {}).get("farms", [{}])[0] if len(final) > p else {}
    tiles = farm.get("tiles", [])
    unlocked = sum(1 for row in tiles for tile in row if tile not in (None, "LOCKED"))
    return {
        "episode_id": record["episode_id"],
        "loss": record["loss"],
        "margin": record["margin"],
        "ppo_reward": record["ppo_reward"],
        "opponent_reward": record["opponent_reward"],
        "final_money": farm.get("money"),
        "unlocked_nonempty_tiles": unlocked,
        "final_farmer": farm.get("farmer"),
        "final_hands": farm.get("hands"),
        "final_tiles": tiles,
        "market_action_counts": dict(market_counts),
        "farmer_action_counts": dict(farmer_counts),
        "sale_timing": {
            product: {"count": len(steps_), "first": min(steps_) if steps_ else None, "last": max(steps_) if steps_ else None}
            for product, steps_ in sale_steps.items()
        },
        "late_actions": record["late_actions"],
    }


rows = [summarize(record) for record in data["records"]]
losses = [row for row in rows if row["loss"]]
wins = [row for row in rows if not row["loss"]]
report = {
    "submission": data["submission"],
    "loss_count": len(losses),
    "win_count": len(wins),
    "losses": losses,
    "wins": wins,
    "pattern_assessment": {
        "loss_margins": [row["margin"] for row in losses],
        "losses_share_same_margin_scale": False,
        "controls_available_in_replay": False,
        "controls_note": "The Kaggle replay exposes actions and observations, not the internal u_market/u_route values; no control values were inferred.",
    },
}
out = Path("reports/step5b/old_loss_gauntlet/submitted_ppo_loss_patterns.json")
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "losses": [(r["episode_id"], r["margin"], r["final_money"], r["unlocked_nonempty_tiles"]) for r in losses],
    "wins": [(r["episode_id"], r["margin"], r["final_money"], r["unlocked_nonempty_tiles"]) for r in wins],
}, indent=2))
print(f"WROTE {out}")
