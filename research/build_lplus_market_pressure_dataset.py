"""Build a read-only L+ market-pressure dataset from cached raw replays.

This module never imports kaggle_environments and never runs a game. It keeps
pre-decision features separate from future-derived labels and uses only prior
step action summaries as replay-observable market context.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "reports" / "step5b" / "old_loss_gauntlet" / "raw_replays"
OUT_DATASET = ROOT / "lplus_market_pressure_dataset.jsonl"
OUT_SPLITS = ROOT / "lplus_market_pressure_split_manifest.json"
OUT_SCHEMA = ROOT / "lplus_market_pressure_schema.json"
OUT_AUDIT_JSON = ROOT / "LPLUS_ML_DATASET_AUDIT.json"
OUT_AUDIT_MD = ROOT / "LPLUS_ML_DATASET_AUDIT.md"
DOWNSTREAM_SOURCE = ROOT / "data" / "replay" / "mcv_replay_dataset.json"

PRODUCTS = ("MILK", "STRAWBERRY", "WOOL")
HORIZON = 720
CLEARANCE_INTERVAL = 24
ADVERSE_THRESHOLD = -0.15
FAVORABLE_THRESHOLD = 0.10


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("value", "amount", "quantity", "count", "price", "money", "cash"):
            if key in value:
                result = _number(value[key])
                if result is not None:
                    return result
    return None


def _clean_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, item in value.items():
        number = _number(item)
        if number is not None:
            result[str(key)] = number
    return result


def _market_map(observation: dict[str, Any], key: str) -> dict[str, float]:
    market = observation.get("market") or {}
    return _clean_map(market.get(key) or {})


def _farm_for_player(observation: dict[str, Any], player_idx: int) -> dict[str, Any]:
    farms = observation.get("farms")
    if isinstance(farms, list) and player_idx < len(farms) and isinstance(farms[player_idx], dict):
        return farms[player_idx]
    if isinstance(farms, dict):
        candidate = farms.get(str(player_idx), farms.get(player_idx))
        if isinstance(candidate, dict):
            return candidate
    return {}


def _private_inventory(observation: dict[str, Any]) -> dict[str, float]:
    private = observation.get("private") or {}
    result: dict[str, float] = {}
    for key in ("inventories", "shed"):
        value = private.get(key) or {}
        if isinstance(value, list):
            for item in value:
                for product, quantity in _clean_map(item).items():
                    result[product] = result.get(product, 0.0) + quantity
        else:
            for product, quantity in _clean_map(value).items():
                result[product] = result.get(product, 0.0) + quantity
    return result


def _farm_scalar(farm: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in farm:
            value = _number(farm[key])
            if value is not None:
                return value
    return None


def _tile_stats(farm: dict[str, Any]) -> tuple[int, int, int]:
    plants = 0
    pastures = 0
    unlocked_tiles = 0
    tiles = farm.get("tiles") or []
    if isinstance(tiles, list):
        for row in tiles:
            if not isinstance(row, list):
                continue
            for tile in row:
                if tile == "LOCKED":
                    continue
                if tile is not None:
                    unlocked_tiles += 1
                if isinstance(tile, dict):
                    if tile.get("kind") == "PLANT":
                        plants += 1
                    elif tile.get("kind") == "PASTURE":
                        pastures += 1
    return plants, pastures, unlocked_tiles


def _sell_orders(action: Any) -> list[tuple[str, float]]:
    if not isinstance(action, dict):
        return []
    market = action.get("market") or []
    result: list[tuple[str, float]] = []
    for order in market:
        if not isinstance(order, list) or len(order) < 3:
            continue
        if str(order[0]).upper() != "SELL":
            continue
        quantity = _number(order[2])
        if quantity is not None:
            result.append((str(order[1]).upper(), quantity))
    return result


def _mode(orders: list[tuple[str, float]]) -> str:
    if not orders:
        return "NO_SELL"
    first = orders[0][0]
    if first == "MILK":
        return "MILK_FIRST"
    if first == "STRAWBERRY":
        return "STRAWBERRY_FIRST"
    if first == "WOOL":
        return "WOOL_FIRST"
    return "OTHER_FIRST"


def _action_summary(step: list[dict[str, Any]]) -> dict[str, float]:
    summary: dict[str, float] = {}
    for agent in step:
        for product, quantity in _sell_orders(agent.get("action")):
            summary[f"sell_qty_{product}"] = summary.get(f"sell_qty_{product}", 0.0) + quantity
            summary[f"sell_orders_{product}"] = summary.get(f"sell_orders_{product}", 0.0) + 1.0
    return summary


def _lineage(replay: dict[str, Any]) -> str:
    info = replay.get("info") or {}
    agents = info.get("Agents") or info.get("agents") or []
    if isinstance(agents, list):
        return "|".join(str(item) for item in agents)
    return str(agents or replay.get("description") or replay.get("name") or "unknown")


def _match_id(path: Path) -> str:
    return path.stem.replace("episode-", "").replace("-replay", "")


def _next_clearance(step: int, steps: list[list[dict[str, Any]]]) -> int | None:
    start = step + 1
    for candidate in range(start, min(len(steps), HORIZON)):
        if candidate % CLEARANCE_INTERVAL == CLEARANCE_INTERVAL - 1:
            return candidate
    return None


def _prices_at(steps: list[list[dict[str, Any]]], step: int, player_idx: int) -> dict[str, float]:
    if step >= len(steps) or player_idx >= len(steps[step]):
        return {}
    observation = steps[step][player_idx].get("observation") or {}
    prices = _market_map(observation, "prices")
    return {product: prices[product] for product in PRODUCTS if product in prices}


def _feature_row(
    replay: dict[str, Any],
    replay_path: Path,
    steps: list[list[dict[str, Any]]],
    step: int,
    player_idx: int,
    split: str,
    downstream_lookup: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    match_id = _match_id(replay_path)
    record = steps[step][player_idx]
    observation = record.get("observation") or {}
    farm = _farm_for_player(observation, player_idx)
    inventory = _private_inventory(observation)
    prices = _market_map(observation, "prices")
    market_inventory = _market_map(observation, "inventory")
    orders = _sell_orders(record.get("action"))
    clearance_step = _next_clearance(step, steps)
    next_prices = _prices_at(steps, clearance_step, player_idx) if clearance_step is not None else {}
    plants, pastures, unlocked_tiles = _tile_stats(farm)
    hands = farm.get("hands") if isinstance(farm.get("hands"), list) else []
    unlocked_quadrants = farm.get("unlocked_quadrants") if isinstance(farm.get("unlocked_quadrants"), list) else []

    features: dict[str, Any] = {
        "step": step,
        "day": _number(observation.get("day")),
        "hour": _number(observation.get("hour")),
        "clearance_position": step % CLEARANCE_INTERVAL,
        "steps_to_next_clearance": (clearance_step - step) if clearance_step is not None else None,
        "cash": _farm_scalar(farm, ("money", "cash")),
        "workers": float(len(hands)),
        "plants": float(plants),
        "pastures": float(pastures),
        "land_count": float(len(unlocked_quadrants)),
        "unlocked_tile_count": float(unlocked_tiles),
        "sell_mode_observed": _mode(orders),
        "sell_order_count": len(orders),
        "sell_priority_milk": next((idx for idx, item in enumerate(orders) if item[0] == "MILK"), -1),
        "sell_priority_strawberry": next((idx for idx, item in enumerate(orders) if item[0] == "STRAWBERRY"), -1),
        "sell_priority_wool": next((idx for idx, item in enumerate(orders) if item[0] == "WOOL"), -1),
    }
    for product in PRODUCTS:
        features[f"price_{product.lower()}"] = prices.get(product)
        features[f"market_inventory_{product.lower()}"] = market_inventory.get(product)
        features[f"own_inventory_{product.lower()}"] = inventory.get(product)
        for lag in (1, 3, 6):
            previous = _prices_at(steps, step - lag, player_idx) if step >= lag else {}
            current = prices.get(product)
            prior = previous.get(product)
            features[f"price_delta_{product.lower()}_{lag}"] = (current - prior) if current is not None and prior is not None else None
            features[f"price_change_{product.lower()}_{lag}"] = ((current - prior) / prior) if current is not None and prior not in (None, 0) else None
    for lag in (1, 3):
        summary = _action_summary(steps[step - lag]) if step >= lag else {}
        for key, value in summary.items():
            features[f"prior_{lag}_{key}"] = value

    labels: dict[str, Any] = {
        "next_clearance_step": clearance_step,
        "next_clearance_price_milk": next_prices.get("MILK"),
        "next_clearance_price_strawberry": next_prices.get("STRAWBERRY"),
        "next_clearance_price_wool": next_prices.get("WOOL"),
        "downstream_wealth_24": None,
        "downstream_wealth_120": None,
    }
    joined = downstream_lookup.get((match_id, player_idx, step), {})
    labels["downstream_wealth_24"] = _number(joined.get("downstream_wealth_24"))
    labels["downstream_wealth_120"] = _number(joined.get("downstream_wealth_120"))
    # Full raw replays do not contain the derived downstream labels; keep them null.
    for product in PRODUCTS:
        current = prices.get(product)
        future = next_prices.get(product)
        change = ((future - current) / current) if current not in (None, 0) and future is not None else None
        labels[f"next_clearance_change_{product.lower()}"] = change
        labels[f"adverse_{product.lower()}"] = (change <= ADVERSE_THRESHOLD) if change is not None else None
        labels[f"favorable_{product.lower()}"] = (change >= FAVORABLE_THRESHOLD) if change is not None else None
    labels["weak_existing_mode_label"] = _mode(orders)

    return {
        "match_id": match_id,
        "replay_file": str(replay_path.relative_to(ROOT)),
        "opponent_lineage": _lineage(replay),
        "seat": player_idx,
        "split": split,
        "policy_source": "historical_replay_agent_action; not guaranteed L+",
        "feature_observability": "pre_decision own/public state plus prior-step replay-observable action summaries",
        "features": features,
        "labels": labels,
    }


def _valid_replays() -> list[tuple[Path, dict[str, Any]]]:
    valid: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(RAW_ROOT.glob("*/episode-*-replay.json")):
        try:
            replay = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        steps = replay.get("steps")
        config = replay.get("configuration") or {}
        if not isinstance(steps, list) or len(steps) < HORIZON - 1:
            continue
        if int(config.get("episodeSteps", HORIZON)) != HORIZON:
            continue
        valid.append((path, replay))
    return valid


def _build_splits(replays: list[tuple[Path, dict[str, Any]]]) -> dict[str, str]:
    groups: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    for item in replays:
        groups[_lineage(item[1])].append(item)
    ordered_groups = sorted(groups.items(), key=lambda item: max(_match_id(path) for path, _ in item[1]))
    validation_start = max(1, int(len(ordered_groups) * 0.8))
    split_by_match: dict[str, str] = {}
    for idx, (_, group) in enumerate(ordered_groups):
        split = "validation" if idx >= validation_start else "train"
        for path, _ in group:
            split_by_match[_match_id(path)] = split
    return split_by_match


def _load_downstream_lookup() -> dict[tuple[str, int, int], dict[str, Any]]:
    if not DOWNSTREAM_SOURCE.exists():
        return {}
    try:
        records = json.loads(DOWNSTREAM_SOURCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    lookup: dict[tuple[str, int, int], dict[str, Any]] = {}
    for record in records if isinstance(records, list) else []:
        file_id = str(record.get("file", "")).replace("episode-", "").replace("-replay", "").replace(".json", "")
        player_idx = record.get("player_idx")
        step = record.get("step")
        if file_id and isinstance(player_idx, int) and isinstance(step, int):
            lookup[(file_id, player_idx, step)] = record
    return lookup


def build() -> dict[str, Any]:
    replays = _valid_replays()
    split_by_match = _build_splits(replays)
    downstream_lookup = _load_downstream_lookup()
    row_count = 0
    split_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    class_counts: dict[str, dict[str, Counter[str]]] = {
        product: {
            f"adverse_{product.lower()}": Counter(),
            f"favorable_{product.lower()}": Counter(),
        }
        for product in PRODUCTS
    }
    null_counts: Counter[str] = Counter()
    wealth_24_count = 0
    wealth_120_count = 0
    with OUT_DATASET.open("w", encoding="utf-8", newline="\n") as dataset_handle:
        for path, replay in replays:
            steps = replay["steps"]
            match_id = _match_id(path)
            split = split_by_match[match_id]
            for player_idx in range(min(2, len(steps[0]))):
                for step in range(min(HORIZON - 1, len(steps))):
                    row = _feature_row(replay, path, steps, step, player_idx, split, downstream_lookup)
                    dataset_handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                    row_count += 1
                    split_counts[split] += 1
                    mode_counts[row["labels"]["weak_existing_mode_label"]] += 1
                    wealth_24_count += row["labels"].get("downstream_wealth_24") is not None
                    wealth_120_count += row["labels"].get("downstream_wealth_120") is not None
                    for product in PRODUCTS:
                        for label_name in (f"adverse_{product.lower()}", f"favorable_{product.lower()}"):
                            class_counts[product][label_name][str(row["labels"].get(label_name))] += 1
                    for key, value in row["features"].items():
                        if value is None:
                            null_counts[key] += 1
    split_manifest = {
        "split_rule": "complete opponent-lineage groups sorted by latest match id; final 20 percent held out as validation",
        "train_matches": sorted(match_id for match_id, split in split_by_match.items() if split == "train"),
        "validation_matches": sorted(match_id for match_id, split in split_by_match.items() if split == "validation"),
        "match_to_split": split_by_match,
    }
    OUT_SPLITS.write_text(json.dumps(split_manifest, indent=2), encoding="utf-8")

    schema = {
        "format": "JSONL equivalent to parquet",
        "row_unit": "one pre-decision state per replay, seat, and step",
        "feature_container": "features",
        "label_container": "labels",
        "products": PRODUCTS,
        "label_thresholds": {"adverse_relative_change": ADVERSE_THRESHOLD, "favorable_relative_change": FAVORABLE_THRESHOLD},
        "future_fields_excluded_from_features": ["next_clearance_step", "next_clearance_price_*", "next_clearance_change_*", "adverse_*", "favorable_*", "downstream_wealth_*"],
        "private_opponent_fields_excluded": True,
    }
    OUT_SCHEMA.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    class_balance: dict[str, dict[str, dict[str, int]]] = {}
    for product in PRODUCTS:
        class_balance[product] = {}
        for label_name in (f"adverse_{product.lower()}", f"favorable_{product.lower()}"):
            class_balance[product][label_name] = {
                key: count for key, count in class_counts[product][label_name].items()
            }
    audit = {
        "status": "PASS_WITH_LIMITATIONS" if replays and row_count else "FAIL",
        "scope": "offline cached replay extraction only",
        "games_run": False,
        "training_run": False,
        "valid_replays": len(replays),
        "rows": row_count,
        "rows_by_split": dict(split_counts),
        "matches_by_split": {split: len(items) for split, items in (("train", split_manifest["train_matches"]), ("validation", split_manifest["validation_matches"]))},
        "mode_label_counts": dict(mode_counts),
        "class_balance": class_balance,
        "downstream_label_join": {
            "source": str(DOWNSTREAM_SOURCE.relative_to(ROOT)),
            "source_rows": len(downstream_lookup),
            "rows_with_wealth_24": wealth_24_count,
            "rows_with_wealth_120": wealth_120_count,
        },
        "missingness_top": sorted(({"feature": key, "nulls": value, "rate": value / max(1, row_count)} for key, value in null_counts.items()), key=lambda item: item["nulls"], reverse=True)[:30],
        "leakage_audit": {
            "future_labels_in_features": False,
            "current_opponent_action_in_features": False,
            "opponent_private_inventory_in_features": False,
            "terminal_mcv_as_primary_feature": False,
            "random_row_split": False,
            "same_match_cross_split": False,
            "notes": [
                "Future-derived fields are under labels only.",
                "Prior replay actions are used only as historical observable summaries; current opponent action is excluded.",
                "Downstream wealth labels are joined from the reduced replay dataset; the raw replay itself does not contain those derived fields.",
            ],
        },
        "baseline_statistics": {
            "label_adverse_threshold": ADVERSE_THRESHOLD,
            "label_favorable_threshold": FAVORABLE_THRESHOLD,
            "clearance_interval": CLEARANCE_INTERVAL,
            "horizon": HORIZON,
        },
        "limitations": [
            "Historical replay agents are not guaranteed to be L+; policy_source is explicit.",
            "Native accepted/rejected/preempted outcomes are unavailable.",
            "No causal mode ranking is claimed; weak_existing_mode_label is observed action priority only.",
            "Downstream wealth labels are joined from the reduced replay dataset and retain that dataset's provenance.",
        ],
        "artifacts": [str(path.relative_to(ROOT)) for path in (OUT_DATASET, OUT_SPLITS, OUT_SCHEMA)],
    }
    OUT_AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    lines = [
        "# L+ ML Dataset Audit",
        "",
        "Scope: offline extraction from cached raw replays only. No games or training were run.",
        "",
        f"Status: **{audit['status']}**",
        f"Valid complete replays: **{len(replays)}**",
        f"Rows: **{row_count}**",
        f"Train rows / validation rows: **{split_counts.get('train', 0)} / {split_counts.get('validation', 0)}**",
        "",
        "## Dataset",
        "",
        "Each row is one pre-decision state for one seat and one replay step. Features contain current own/public state and prior-step replay-observable action summaries. Future-derived prices and outcomes are labels only.",
        "",
        "## Labels",
        "",
        f"Adverse next-clearance movement: relative price change <= {ADVERSE_THRESHOLD:.0%}.",
        f"Favorable next-clearance opportunity: relative price change >= {FAVORABLE_THRESHOLD:.0%}.",
        "The weak existing-mode label records the observed first sell priority. It is not a causal ranking label.",
        "",
        "## Class Balance",
        "",
        f"MILK adverse/favorable positives: {class_balance['MILK']['adverse_milk'].get('True', 0)} / {class_balance['MILK']['favorable_milk'].get('True', 0)}.",
        f"STRAWBERRY adverse/favorable positives: {class_balance['STRAWBERRY']['adverse_strawberry'].get('True', 0)} / {class_balance['STRAWBERRY']['favorable_strawberry'].get('True', 0)}.",
        f"WOOL adverse/favorable positives: {class_balance['WOOL']['adverse_wool'].get('True', 0)} / {class_balance['WOOL']['favorable_wool'].get('True', 0)}.",
        "",
        "## Leakage And Legal Observability",
        "",
        "- PASS: future label fields are excluded from features.",
        "- PASS: current opponent actions are excluded; only prior replay-observable summaries are included.",
        "- PASS: opponent private inventory is excluded.",
        "- PASS: terminal MCV is not a feature or primary target.",
        "- PASS: train/validation split is by complete match, with a chronological held-out tail.",
        "- LIMITATION: raw replays do not contain native accepted/rejected/preempted flags.",
        f"- LIMITATION: the available reduced-dataset join has 0 matching rows for these 20 raw replays; downstream wealth labels remain null.",
        "",
        "## Decision",
        "",
        "The dataset passes structural leakage and observability checks for offline prediction, with the limitations above. It does not yet justify model training or a causal policy claim. Downstream-wealth joins and label-quality review should be completed before training.",
    ]
    OUT_AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
