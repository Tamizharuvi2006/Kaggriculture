"""Diagnostic-only strategy layer built on the proven fixed-v18 policy."""

from __future__ import annotations

import importlib.util
import copy
import time
from pathlib import Path
from typing import Any

from apex_next.ml_engine.training.train_strategy_selector_ppo import APEX4_PATH


SCHEDULE_STEPS = frozenset({120, 240, 360, 480, 600})

# Diagnostic-only interface contract. The value is an additive score bias at
# v18's existing daily market-expert selection point, never an action override.
MARKET_PREFERENCE_MIN = -0.25
MARKET_PREFERENCE_MAX = 0.25
MARKET_PREFERENCES = {
    "BALANCED": (None, 0.0),
    "LIVESTOCK": ("mohit", 0.25),
    "PREMIUM": ("manual_player", 0.25),
    "WHEAT_RUSH": ("dmitry_larko", 0.25),
}
BOARD_ROUTE_TARGET = "dmitry_larko"
BOARD_ROUTE_BIAS = 0.25
BOARD_ROUTE_DISTANCE_STRENGTH = 0.5


def _load_v18_module(profile_name: str, module_suffix: int) -> Any:
    module_name = f"apex4_v18_strategy_{profile_name.lower()}_{module_suffix}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, APEX4_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {APEX4_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Preserve the proven v18 schedule. Profile fields are applied only by the
    # adapter below, never by replacing the v18 action generator.
    module.configure_strategy({"use_fixed_schedule": True, "fixed_schedule_version": "v18"})
    module._DIAGNOSTIC_BASE_MARKET_BIAS = copy.deepcopy(module._V18_RUNTIME["market_bias_by_seat"])
    target, preference = MARKET_PREFERENCES.get(profile_name, MARKET_PREFERENCES["BALANCED"])
    bounded_preference = max(MARKET_PREFERENCE_MIN, min(MARKET_PREFERENCE_MAX, float(preference)))
    if target is not None and bounded_preference and profile_name != "PREMIUM":
        for seat_bias in module._V18_RUNTIME["market_bias_by_seat"].values():
            if target in seat_bias:
                seat_bias[target] += bounded_preference
    if profile_name == "WHEAT_RUSH":
        module._V18_RUNTIME["board_distance_strength"] = BOARD_ROUTE_DISTANCE_STRENGTH
        for seat_bias in module._V18_RUNTIME["board_bias_by_seat"].values():
            if BOARD_ROUTE_TARGET in seat_bias:
                seat_bias[BOARD_ROUTE_TARGET] += BOARD_ROUTE_BIAS
    return module


def _prioritize_existing_order(market: list[list[Any]], predicate) -> None:
    """Reorder an existing v18 order without changing the order set."""
    target = next((order for order in market if predicate(order)), None)
    if target is None:
        return
    target_index = market.index(target)
    earlier = next(
        (index for index, order in enumerate(market[:target_index]) if order and order[0] in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}),
        None,
    )
    if earlier is not None:
        market[earlier], market[target_index] = market[target_index], market[earlier]


def _apply_v18_profile(action: dict[str, Any], profile_name: str, step: int, observation: dict[str, Any]) -> dict[str, Any]:
    return action


def configured_v18_agent(profile_name: str, module_suffix: int):
    module = _load_v18_module(profile_name, module_suffix)
    base_agent = module.agent

    def agent(obs: dict[str, Any], configuration: Any = None) -> dict[str, Any]:
        action = base_agent(obs, configuration)
        if not isinstance(action, dict):
            return action
        step = int(obs.get("step", 0)) if isinstance(obs, dict) else 0
        return _apply_v18_profile(action, profile_name, step, obs)

    return agent
