"""Executable Step 3F opponent archetypes for data diversity pilots.

These policies are intentionally simple overlays around the sealed APEX4
executor. They are used only for ML data generation and never modify or replace
the production submission artifact.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from apex_next.ml_engine.env_wrapper import call_agent, load_agent, sanitize_action


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APEX4_PATH = PROJECT_ROOT / "APEX4_SUBMISSION_FINAL.py"
AgentFn = Callable[[dict[str, Any], Any], dict[str, list[Any]]]

_BASE_AGENT: AgentFn | None = None


def crop_heavy_agent(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    """Plant a real strawberry-heavy field using public board actions."""

    step = _step(obs)
    farm = _own_farm(obs)
    unit_positions = [farm.get("farmer", [4, 4])] + list(farm.get("hands", []) or [])
    unit_actions = [_crop_unit_action(obs, position) for position in unit_positions]

    market: list[list[Any]] = []
    if step < 220:
        market.append(["BUY_SEED", "STRAWBERRY", 10])
    if step < 180 and len(unit_positions) < 10:
        market.extend([["HIRE"], ["HIRE"]])
    if 40 <= step < 170 and step % 24 in {1, 2, 3}:
        market.append(["BUY_LAND"])

    return {
        "farmer": unit_actions[0] if unit_actions else ["PASS"],
        "hands": unit_actions[1:],
        "market": _cap_market(market),
    }


def aggressive_expand_agent(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    """Prioritize early land orders so the public farm gets ahead by step 200."""

    action = _base_action(obs, config)
    step = _step(obs)
    market = list(action["market"])
    if step < 190:
        market = [["BUY_LAND"], ["BUY_LAND"], ["HIRE"]] + market
    action["market"] = _cap_market(market)
    return action


def market_manipulator_agent(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    """Create a measurable market-focused action signature.

    The policy repeatedly submits product buy/sell orders, creating action
    telemetry that can be measured conservatively. It still runs through the
    real environment and action sanitizer.
    """

    action = _base_action(obs, config)
    step = _step(obs)
    product = "WHEAT" if step < 360 else "STRAWBERRY"
    churn_orders = [
        ["BUY_PRODUCT", product, 1],
        ["BUY_PRODUCT", product, 1],
        ["BUY_PRODUCT", product, 1],
        ["SELL", product, 1],
        ["SELL", product, 1],
    ]
    action["market"] = _cap_market(churn_orders + list(action["market"]))
    return action


def _base_action(obs: dict[str, Any], config: Any) -> dict[str, list[Any]]:
    global _BASE_AGENT
    if _BASE_AGENT is None:
        _BASE_AGENT = load_agent(APEX4_PATH)
    return copy.deepcopy(sanitize_action(call_agent(_BASE_AGENT, obs, config)))


def _without_commands(market: list[Any], commands: set[str]) -> list[list[Any]]:
    return [list(order) for order in market if isinstance(order, list) and (not order or order[0] not in commands)]


def _cap_market(market: list[Any]) -> list[list[Any]]:
    return [list(order) for order in market if isinstance(order, list)][:10]


def _step(obs: dict[str, Any]) -> int:
    try:
        return int(obs.get("step", 0))
    except (TypeError, ValueError):
        return 0


def _own_farm(obs: dict[str, Any]) -> dict[str, Any]:
    farms = obs.get("farms") if isinstance(obs, dict) else None
    if isinstance(farms, list) and farms and isinstance(farms[0], dict):
        return farms[0]
    return {}


def _crop_unit_action(obs: dict[str, Any], position: Any) -> list[Any]:
    pos = _position(position)
    farm = _own_farm(obs)
    tiles = farm.get("tiles", [])
    tile = _tile_at(tiles, pos)
    private = obs.get("private", {}) if isinstance(obs, dict) else {}
    seeds = private.get("seeds", {}) if isinstance(private, dict) else {}
    strawberry_seeds = int(seeds.get("STRAWBERRY", 0) or 0) if isinstance(seeds, dict) else 0

    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if not tile.get("watered_today", False):
            return ["WATER"]
        target = _nearest_crop_target(tiles, pos)
        return _move_toward(pos, target)
    if tile is None and strawberry_seeds > 0:
        return ["PLANT", "STRAWBERRY"]

    target = _nearest_crop_target(tiles, pos)
    return _move_toward(pos, target)


def _nearest_crop_target(tiles: Any, pos: tuple[int, int]) -> tuple[int, int]:
    candidates: list[tuple[int, int]] = []
    if isinstance(tiles, list):
        for y, row in enumerate(tiles):
            if not isinstance(row, list):
                continue
            for x, tile in enumerate(row):
                if tile is None:
                    candidates.append((x, y))
    if not candidates:
        return pos
    return min(candidates, key=lambda item: abs(item[0] - pos[0]) + abs(item[1] - pos[1]))


def _tile_at(tiles: Any, pos: tuple[int, int]) -> Any:
    x, y = pos
    if isinstance(tiles, list) and 0 <= y < len(tiles) and isinstance(tiles[y], list) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return None


def _position(value: Any) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            pass
    return 4, 4


def _move_toward(pos: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = pos
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return ["PASS"]
