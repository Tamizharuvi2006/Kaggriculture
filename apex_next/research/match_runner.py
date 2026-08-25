"""Paired match runner for the research lab.

Runs baseline (production submission.py, IMMUTABLE) vs candidate under the
real kaggle_environments kaggriculture environment, seat-balanced per seed.

Contract:
  - baseline is always loaded from submission.py and never modified.
  - one match per worker process; all state is per-process.
  - each result carries: MCVs, winner, candidate PASS turns, candidate
    latency (mean/max ms), and the per-match regime tag derived from the
    market price series exactly as regime_detector calibrates it.
"""
import importlib.util
import json
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor

import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE_PATH = os.path.join(_PROJECT_ROOT, "submission.py")
CANDIDATE_PATH = os.path.join(
    _PROJECT_ROOT, "apex_next", "research", "EXP-0113", "candidate", "candidate_submission.py"
)

EPISODE_STEPS = 720
DECISIVE_PRODUCTS = ("STRAWBERRY", "MELON")
COLLAPSE_DRIFT = -0.30


def _load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _price_of(value):
    if isinstance(value, dict):
        return value.get("price")
    return value


def _classify_regime(prices_by_product):
    """Same thresholds as regime_detector: any 3-step window with drift <= -30% = SUPPLY_COLLAPSE."""
    tags = []
    for product, series in prices_by_product.items():
        if len(series) < 4:
            continue
        worst = None
        for i in range(3, len(series)):
            base = series[i - 3]
            if base <= 0:
                continue
            drift = (series[i] - base) / base
            if worst is None or drift < worst:
                worst = drift
        if worst is not None and worst <= COLLAPSE_DRIFT:
            tags.append({"product": product, "min_drift3": round(worst, 4)})
    return tags


def _collect_price_series(state_history):
    series = {}
    for step in state_history:
        for agent in step:
            obs = agent.get("observation") or {}
            prices = (obs.get("market") or {}).get("prices") or {}
            for product in DECISIVE_PRODUCTS:
                price = _price_of(prices.get(product))
                if price is None:
                    continue
                series.setdefault(product, []).append(float(price))
    return series


def _count_pass_turns(state_history, idx):
    count = 0
    for step in state_history:
        action = step[idx].get("action") or {}
        if action.get("farmer") == ["PASS"]:
            count += 1
    return count


def run_single_match(seed, swap=False, candidate_path=None, baseline_path=None):
    """Run baseline vs candidate once on `seed`. Returns a result dict."""
    start = time.time()
    try:
        base_mod = _load_agent(baseline_path or BASELINE_PATH, f"base_{seed}")
        cand_mod = _load_agent(candidate_path or CANDIDATE_PATH, f"cand_{seed}")
        p0, p1 = (cand_mod.agent, base_mod.agent) if swap else (base_mod.agent, cand_mod.agent)
        base_idx, cand_idx = (1, 0) if swap else (0, 1)

        env = kaggle_environments.make(
            "kaggriculture", configuration={"episodeSteps": EPISODE_STEPS, "seed": seed}
        )
        state_history = env.run([p0, p1])
        final = state_history[-1]

        base_mcv = float(final[base_idx].get("reward", 0) or final[base_idx]["observation"]["farms"][base_idx]["money"])
        cand_mcv = float(final[cand_idx].get("reward", 0) or final[cand_idx]["observation"]["farms"][cand_idx]["money"])

        metrics = getattr(cand_mod, "_STATE", {}).get("metrics") or {}
        latency = metrics.get("latency_ms", [])
        intervention = metrics.get("suppressed_orders", 0) or metrics.get("deferred_orders", 0)
        cand_pass = metrics.get("pass_turns") or _count_pass_turns(state_history, cand_idx)
        result = {
            "seed": seed,
            "swap": swap,
            "base_mcv": base_mcv,
            "cand_mcv": cand_mcv,
            "win": cand_mcv > base_mcv,
            "base_pass_turns": _count_pass_turns(state_history, base_idx),
            "cand_pass_turns": cand_pass,
            "added_pass_turns": cand_pass - _count_pass_turns(state_history, base_idx),
            "cand_suppressed_orders": intervention,
            "cand_latency_mean_ms": round(sum(latency) / max(1, len(latency)), 3),
            "cand_latency_max_ms": round(max(latency) if latency else 0.0, 3),
            "regime_tags": _classify_regime(_collect_price_series(state_history)),
            "runtime_s": round(time.time() - start, 1),
            "error": None,
        }
        return result
    except Exception as exc:  # noqa: BLE001
        return {
            "seed": seed,
            "swap": swap,
            "base_mcv": 0.0,
            "cand_mcv": 0.0,
            "win": False,
            "base_pass_turns": 0,
            "cand_pass_turns": 0,
            "added_pass_turns": 0,
            "cand_suppressed_orders": 0,
            "cand_latency_mean_ms": 0.0,
            "cand_latency_max_ms": 0.0,
            "regime_tags": [],
            "runtime_s": round(time.time() - start, 1),
            "error": str(exc),
        }


def run_paired(seeds, max_workers=4, seat_balanced=True, progress_file=None, candidate_path=None, baseline_path=None):
    """Run each seed TWICE (both seat orders) and merge per-seed results.

    Required because kaggriculture is seat-asymmetric (board_by_seat): a single
    match compares candidates on unequal grounds.  Merged record aggregates the
    two seat configs (MCVs averaged, win points summed) so every seed
    contributes an even comparison.
    """
    cand_path = candidate_path or CANDIDATE_PATH
    base_path = baseline_path or BASELINE_PATH
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_seed_pair, seed, cand_path, base_path): seed for seed in seeds}
        done = 0
        for fut in futures:
            res = fut.result()
            results.append(res)
            done += 1
            if progress_file and done % 5 == 0:
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=1, default=str)
                    print(f"  progress: {done}/{len(seeds)} seeds -> {progress_file}", flush=True)
    results.sort(key=lambda r: r["seed"])
    if progress_file:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, default=str)
    return results


def _run_seed_pair(seed, candidate_path, baseline_path):
    """Two matches per seed (seat orders 0 and 1); merge into one result."""
    errors = []
    try:
        m0 = run_single_match(seed, swap=False, candidate_path=candidate_path, baseline_path=baseline_path)
        m1 = run_single_match(seed, swap=True, candidate_path=candidate_path, baseline_path=baseline_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "seed": seed,
            "base_mcv": 0.0,
            "cand_mcv": 0.0,
            "win_points": 0.0,
            "base_mcvs": [0.0],
            "cand_mcvs": [0.0],
            "cand_pass_turns": 0,
            "added_pass_turns": 0,
            "cand_suppressed_orders": 0,
            "cand_latency_mean_ms": 0.0,
            "cand_latency_max_ms": 0.0,
            "regime_tags": [],
            "error": str(exc),
        }

    def win_points(match):
        if match["cand_mcv"] > match["base_mcv"]:
            return 1.0
        if match["cand_mcv"] == match["base_mcv"]:
            return 0.5
        return 0.0

    base_mcvs = [m0["base_mcv"], m1["base_mcv"]]
    cand_mcvs = [m0["cand_mcv"], m1["cand_mcv"]]
    latency_means = [m0["cand_latency_mean_ms"], m1["cand_latency_mean_ms"]]
    return {
        "seed": seed,
        "base_mcv": sum(base_mcvs) / 2.0,
        "cand_mcv": sum(cand_mcvs) / 2.0,
        "win_points": win_points(m0) + win_points(m1),
        "base_mcvs": base_mcvs,
        "cand_mcvs": cand_mcvs,
        "cand_pass_turns": m0["cand_pass_turns"] + m1["cand_pass_turns"],
        "added_pass_turns": m0.get("added_pass_turns", 0) + m1.get("added_pass_turns", 0),
        "cand_suppressed_orders": m0["cand_suppressed_orders"] + m1["cand_suppressed_orders"],
        "cand_latency_mean_ms": round(sum(latency_means) / 2.0, 3),
        "cand_latency_max_ms": max(m0["cand_latency_max_ms"], m1["cand_latency_max_ms"]),
        "regime_tags": m0.get("regime_tags", []),
        "error": None,
    }


def summarize(results):
    if not results:
        return {}
    base_mcvs = [v for r in results for v in r.get("base_mcvs", [])]
    cand_mcvs = [v for r in results for v in r.get("cand_mcvs", [])]
    win_points = sum(r.get("win_points", 0.0) for r in results)
    errors = sum(1 for r in results if r.get("error"))
    matches = 2 * len(results)
    return {
        "n": len(results),
        "matches": matches,
        "win_rate": round(win_points / matches, 4),
        "wins": round(win_points, 1),
        "errors": errors,
        "base_mean_mcv": round(sum(base_mcvs) / len(base_mcvs), 1),
        "cand_mean_mcv": round(sum(cand_mcvs) / len(cand_mcvs), 1),
        "delta_mean_mcv": round(sum(cand_mcvs) / len(cand_mcvs) - sum(base_mcvs) / len(base_mcvs), 1),
        "base_std_mcv": round(_std(base_mcvs), 1),
        "cand_std_mcv": round(_std(cand_mcvs), 1),
        "base_p05_mcv": round(_quantile(sorted(base_mcvs), 0.05), 1),
        "cand_p05_mcv": round(_quantile(sorted(cand_mcvs), 0.05), 1),
        "max_added_pass_turns": max((r.get("added_pass_turns", 0) for r in results), default=0),
        "latency_mean_ms": round(sum(r["cand_latency_mean_ms"] for r in results) / len(results), 3),
        "latency_max_ms": max((r["cand_latency_max_ms"] for r in results), default=0.0),
    }


def _std(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def _quantile(sorted_values, q):
    if not sorted_values:
        return 0.0
    idx = max(0, min(len(sorted_values) - 1, int(q * len(sorted_values))))
    return sorted_values[idx]
