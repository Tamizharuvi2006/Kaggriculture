"""EXP-0113 candidate: regime-gated gentle-rebound exit overlay.

Variable family: Pricing (market-only overlay).
Baseline: D:\\Kaggriculture\\submission.py (APEX 3.6 PROD) -- loaded immutable, never
modified.  This module ONLY redefines the outer entry point to apply the
hypothesised overlay to the baseline's market orders.

Mechanism (from EXP-0113_HYPOTHESIS_CARD.md):
  During a confirmed SUPPLY_COLLAPSE of a decisive product (STRAWBERRY/MELON,
  3-step price drift <= -30%), suppress SELL orders of the collapsing product
  until (a) the 3-step drift turns positive or (b) the price recovers above
  its 24-step moving average.  Sales resume automatically on recovery.

Constraints honoured (falsification graveyard):
  - No static price thresholds (Phase 75-76 falsified).
  - No batch capping / unilateral holding without regime evidence (Phase 80-81).
  - No full-engine changes; fixed schedule + dynamic entrypoint untouched.
"""
import sys
import time

sys.path.insert(0, r"D:\Kaggriculture")

import submission as _BASELINE

DECISIVE_PRODUCTS = ("STRAWBERRY", "MELON")
COLLAPSE_DRIFT = -0.30
REBOUND_LOOKBACK = 24
HISTORY_CAP = 60

_STATE = {
    "history": {},
    "prev_step": {},
    "collapsed": {},
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
        _STATE["collapsed"][player] = 0
    _STATE["prev_step"][player] = step
    prices = (obs.get("market") or {}).get("prices") or {}
    hist = _STATE["history"].setdefault(player, {})
    for product in DECISIVE_PRODUCTS:
        price = _price_of(prices.get(product))
        if price is None:
            continue
        series = hist.setdefault(product, [])
        series.append(float(price))
        if len(series) > HISTORY_CAP:
            del series[: len(series) - HISTORY_CAP]


def _drift3(series):
    if len(series) < 4:
        return None
    base = series[-4]
    if base <= 0:
        return None
    return (series[-1] - base) / base


def _above_ma24(series):
    if len(series) < REBOUND_LOOKBACK:
        return None
    return series[-1] >= sum(series[-REBOUND_LOOKBACK:]) / REBOUND_LOOKBACK


def _apply_collapse_gentle_rebound(obs, action):
    _update_history(obs)
    player = int(obs.get("player", 0))
    orders = action.get("market") or []
    if not orders:
        return action
    hist = _STATE["history"].get(player, {})
    kept = []
    removed = 0
    for order in orders:
        if not order or order[0] != "SELL" or len(order) < 2 or order[1] not in DECISIVE_PRODUCTS:
            kept.append(order)
            continue
        series = hist.get(order[1]) or []
        drift = _drift3(series)
        above_ma = _above_ma24(series)
        if drift is None or above_ma is None:
            kept.append(order)
            continue
        if drift <= COLLAPSE_DRIFT and not above_ma:
            removed += 1
        else:
            kept.append(order)
    if removed:
        _STATE["collapsed"][player] = _STATE["collapsed"].get(player, 0) + removed
        _STATE["metrics"]["suppressed_orders"] += removed
    action["market"] = kept
    return action


def agent(obs, configuration=None):
    t0 = time.perf_counter()
    action = _BASELINE.agent(obs, configuration)
    action = _apply_collapse_gentle_rebound(obs, action)
    ms = (time.perf_counter() - t0) * 1000.0
    metrics = _STATE["metrics"]
    metrics["total_steps"] += 1
    metrics["latency_ms"].append(ms)
    if action.get("farmer") == ["PASS"]:
        metrics["pass_turns"] += 1
    return action
