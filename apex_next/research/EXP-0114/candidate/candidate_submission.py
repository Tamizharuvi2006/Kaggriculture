"""EXP-0114 candidate: trend-filtered sell suppression overlay.

Variable family: Pricing (market-only overlay).
Baseline: D:\\Kaggriculture\\submission.py (APEX 3.6 PROD) -- loaded immutable, never
modified.  This module ONLY redefines the outer entry point to apply the
hypothesised overlay to the baseline's market orders.

Mechanism (from EXP-0114_HYPOTHESIS_CARD.md):
  Suppress SELL orders of a decisive product (STRAWBERRY/MELON) while its price
  trades below its 24-step moving average; release sales when the price recovers
  at/above the MA.  Suppression is capped at 48 consecutive below-MA steps per
  product to bound the tail risk of holding through an extended bear market.

Parent: EXP-0113 (FALSIFIED -- gate too narrow, direction positive).
"""
import sys
import time

sys.path.insert(0, r"D:\Kaggriculture")

import submission as _BASELINE

DECISIVE_PRODUCTS = ("STRAWBERRY", "MELON")
MA_LOOKBACK = 24
HOLD_CAP_STEPS = 48
HISTORY_CAP = 60

_STATE = {
    "history": {},
    "below_ma_steps": {},
    "prev_step": {},
    "suppressed": {},
    "metrics": {"pass_turns": 0, "total_steps": 0, "latency_ms": [], "suppressed_orders": 0},
}


def _price_of(value):
    if isinstance(value, dict):
        return value.get("price")
    return value


def _update_history(obs):
    player = int(obs.get("player", 0))
    step = int(obs.get("step", 0))
    if step < _STATE["prev_step"].get(player, step):
        _STATE["history"][player] = {}
        _STATE["below_ma_steps"][player] = {}
        _STATE["suppressed"][player] = 0
    _STATE["prev_step"][player] = step
    prices = (obs.get("market") or {}).get("prices") or {}
    hist = _STATE["history"].setdefault(player, {})
    below = _STATE["below_ma_steps"].setdefault(player, {})
    for product in DECISIVE_PRODUCTS:
        price = _price_of(prices.get(product))
        if price is None:
            continue
        series = hist.setdefault(product, [])
        series.append(float(price))
        if len(series) > HISTORY_CAP:
            del series[: len(series) - HISTORY_CAP]
        if len(series) >= MA_LOOKBACK:
            if price < sum(series[-MA_LOOKBACK:]) / MA_LOOKBACK:
                below[product] = below.get(product, 0) + 1
            else:
                below[product] = 0


def _apply_trend_filter(obs, action):
    _update_history(obs)
    player = int(obs.get("player", 0))
    orders = action.get("market") or []
    if not orders:
        return action
    hist = _STATE["history"].get(player, {})
    below = _STATE["below_ma_steps"].get(player, {})
    kept = []
    removed = 0
    for order in orders:
        if not order or order[0] != "SELL" or len(order) < 2 or order[1] not in DECISIVE_PRODUCTS:
            kept.append(order)
            continue
        product = order[1]
        series = hist.get(product) or []
        if len(series) < MA_LOOKBACK:
            kept.append(order)
            continue
        below_steps = below.get(product, 0)
        if below_steps and below_steps <= HOLD_CAP_STEPS:
            removed += 1
        else:
            kept.append(order)
    if removed:
        _STATE["suppressed"][player] = _STATE["suppressed"].get(player, 0) + removed
        _STATE["metrics"]["suppressed_orders"] += removed
    action["market"] = kept
    return action


def agent(obs, configuration=None):
    t0 = time.perf_counter()
    action = _BASELINE.agent(obs, configuration)
    action = _apply_trend_filter(obs, action)
    ms = (time.perf_counter() - t0) * 1000.0
    metrics = _STATE["metrics"]
    metrics["total_steps"] += 1
    metrics["latency_ms"].append(ms)
    if action.get("farmer") == ["PASS"]:
        metrics["pass_turns"] += 1
    return action
