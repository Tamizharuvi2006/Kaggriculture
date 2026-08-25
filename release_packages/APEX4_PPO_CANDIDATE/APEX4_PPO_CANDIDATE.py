"""Candidate APEX4 entrypoint with frozen Step 5B NumPy inference."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from feature_extractor import extract_features
from step5b_numpy_inference import DECISION_STEP, predict


ROOT = Path(__file__).resolve().parent
SEALED_PATH = ROOT / "APEX4_SUBMISSION_FINAL.py"
CONTROL_LIMIT = 0.25


def _load_sealed(module_suffix: str):
    spec = importlib.util.spec_from_file_location(f"sealed_apex4_{module_suffix}", SEALED_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load sealed APEX4 from {SEALED_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sealed = _load_sealed("base")
_selected_agent = None
_selected_step = None


def _bounded(value: float) -> float:
    return max(-CONTROL_LIMIT, min(CONTROL_LIMIT, float(value)))


def _select_agent(observation: dict, step: int):
    global _selected_agent, _selected_step
    features = extract_features(observation)
    result = predict(features)
    market = _bounded(float(result["controls"][0]))
    route = _bounded(float(result["controls"][1]))

    # Load a fresh in-memory copy so the sealed module on disk is untouched.
    selected = _load_sealed(f"selected_{step}")
    selected.configure_strategy({"use_fixed_schedule": True, "fixed_schedule_version": "v18"})
    if market:
        target = "mohit" if market > 0 else "dmitry_larko"
        for seat_bias in selected._V18_RUNTIME["market_bias_by_seat"].values():
            seat_bias[target] += abs(market)
    if route:
        target = "dmitry_larko" if route > 0 else "mohit"
        selected._V18_RUNTIME["board_distance_strength"] = 0.5
        for seat_bias in selected._V18_RUNTIME["board_bias_by_seat"].values():
            seat_bias[target] += abs(route)
    _selected_step = step
    _selected_agent = selected.agent
    return _selected_agent


def agent(observation, configuration=None):
    """Kaggle-compatible entrypoint with a fixed-v18 fallback."""
    global _selected_agent, _selected_step
    try:
        step = int(observation.get("step", 0)) if isinstance(observation, dict) else 0
        if step == 0:
            _selected_agent = None
            _selected_step = None
        if _selected_agent is None and step >= DECISION_STEP:
            _select_agent(observation, step)
        active = _selected_agent or _sealed.agent
        return active(observation, configuration)
    except Exception:
        # Preserve the sealed APEX4 failure-safe behavior.
        return _sealed.agent(observation, configuration)
