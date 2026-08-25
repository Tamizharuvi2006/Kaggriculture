"""Diagnostic two-control adapter layered on the fixed-v18 runtime."""

from __future__ import annotations

import copy
import importlib.util
import time
from pathlib import Path
from typing import Any

from apex_next.ml_engine.training.train_strategy_selector_ppo import APEX4_PATH


CONTROL_MIN = -0.25
CONTROL_MAX = 0.25
ROUTE_DISTANCE_STRENGTH = 0.5


def clamp_control(value: float) -> float:
    return max(CONTROL_MIN, min(CONTROL_MAX, float(value)))


def configured_two_control_agent(market_preference: float = 0.0, route_preference: float = 0.0, module_suffix: int = 0):
    """Load fixed v18 and apply only bounded expert/route score preferences."""
    market = clamp_control(market_preference)
    route = clamp_control(route_preference)
    module_name = f"apex4_two_control_{module_suffix}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, APEX4_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {APEX4_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure_strategy({"use_fixed_schedule": True, "fixed_schedule_version": "v18"})

    if market:
        target = "mohit" if market > 0 else "dmitry_larko"
        for seat_bias in module._V18_RUNTIME["market_bias_by_seat"].values():
            seat_bias[target] += abs(market)
    if route:
        target = "dmitry_larko" if route > 0 else "mohit"
        module._V18_RUNTIME["board_distance_strength"] = ROUTE_DISTANCE_STRENGTH
        for seat_bias in module._V18_RUNTIME["board_bias_by_seat"].values():
            seat_bias[target] += abs(route)
    return module.agent
