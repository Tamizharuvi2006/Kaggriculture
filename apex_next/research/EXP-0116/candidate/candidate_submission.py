"""EXP-0116 candidate: cash-engine hold overlay (milk/wool sell timing).

Variable family: Pricing (market-only overlay; last order-level variant).
Baseline: D:\\Kaggriculture\\submission.py (APEX 3.6 PROD) -- loaded immutable, never
modified.  This module ONLY redefines the outer entry point to apply the
hypothesised overlay to the baseline's market orders.

Mechanism (from EXP-0116_HYPOTHESIS_CARD.md):
  While a decisive product (STRAWBERRY/MELON) is in a confirmed SUPPLY_COLLAPSE
  (3-step price drift <= -30%), suppress SELL orders of MILK and WOOL -- the
  champion's daily revenue engine -- until the decisive product's 3-step drift
  turns >= 0 or a hard cap of 24 steps (1 day).

Parents: EXP-0113/0115 (inert), EXP-0114 (over-broad).
"""
import sys
import time

sys.path.insert(0, r"D:\Kaggriculture")

import submission as _BASELINE

DECISIVE_PRODUCTS = ("STRAWBERRY", "MELON")
HELD_PRODUCTS = ("MILK", "WOOL")
COLLAPSE_DRIFT = -0.30
REARM_DRIFT = 0.0
HOLD_CAP_STEPS = 24
HISTORY_CAP = 60

_STATE = {
    "history": {},
    "hold_steps": {},
    "prev_step": {},
    "held": {},
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
        _STATE["hold_steps"][player] = {}
        _STATE["held"][player] = 0
    _STATE["prev_step"][player] = step
    prices = (obs.get("market") or {}).get("prices") or {}
    hist = _STATE["history"].setdefault(player, {})
    holds = _STATE["hold_steps"].setdefault(player, {})
    for product in DECISIVE_PRODUCTS:
        price = _price_of(prices.get(product))
        if price is None:
            continue
        series = hist.setdefault(product, [])
        series.append(float(price))
        if len(series) > HISTORY_CAP:
            del series[: len(series) - HISTORY_CAP]
        if len(series) >= 4:
            base = series[-4]
            drift = (series[-1] - base) / base if base > 0 else 1.0
            if drift <= COLLAPSE_DRIFT:
                holds[product] = holds.get(product, 0) + 1
            elif drift >= REARM_DRIFT:
                holds[product] = 0
            else:
                holds[product] = holds.get(product, 0) + 1


def _collapse_active(player):
    holds = _STATE["hold_steps"].get(player, {})
    return any(steps > 0 and steps <= HOLD_CAP_STEPS for steps in holds.values())


def _apply_cash_engine_hold(obs, action):
    _update_history(obs)
    player = int(obs.get("player", 0))
    orders = action.get("market") or []
    if not orders or not _collapse_active(player):
        return action
    kept = []
    removed = 0
    for order in orders:
        if (
            order and order[0] == "SELL" and len(order) >= 2
            and order[1] in HELD_PRODUCTS
        ):
            removed += 1
        else:
            kept.append(order)
    if removed:
        _STATE["held"][player] = _STATE["held"].get(player, 0) + removed
        _STATE["metrics"]["suppressed_orders"] += removed
    action["market"] = kept
    return action


def agent(obs, configuration=None):
    t0 = time.perf_counter()
    action = _BASELINE.agent(obs, configuration)
    action = _apply_cash_engine_hold(obs, action)
    ms = (time.perf_counter() - t0) * 1000.0
    metrics = _STATE["metrics"]
    metrics["total_steps"] += 1
    metrics["latency_ms"].append(ms)
    if action.get("farmer") == ["PASS"]:
        metrics["pass_turns"] += 1
    return action