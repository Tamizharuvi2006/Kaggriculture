from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.training.collect_expert_demos import APEX35_PATH, APEX4_PATH, V18_PATH, _pass_agent

PACKAGE = PROJECT_ROOT / "release_packages" / "APEX4_PPO_FINAL_SINGLE_20260821.zip"
FOUR_OPPONENTS = PROJECT_ROOT / "reports" / "step5b" / "candidate_vs_four_opponents_32.json"
MARKET_TIMING = PROJECT_ROOT / "reports" / "step5b" / "market_timing_diagnostic" / "market_timing_diagnostic.json"
OUT = PROJECT_ROOT / "reports" / "step5b" / "milk_sell_counterfactual"
PRODUCT = "MILK"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opponent(opponent_id: str, index: int):
    if opponent_id == "pass_only":
        return _pass_agent
    paths = {
        "apex35_live_submission": APEX35_PATH,
        "apex4_self_play": APEX4_PATH,
        "v18_baseline": V18_PATH,
    }
    return _load(paths[opponent_id], f"milk_cf_opp_{opponent_id}_{index}").agent


def _obs(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("observation"), dict):
        return entry["observation"]
    return {}


def _farm(obs: dict[str, Any], player: int) -> dict[str, Any]:
    farms = obs.get("farms", [])
    return farms[player] if isinstance(farms, list) and player < len(farms) and isinstance(farms[player], dict) else {}


def _prices(obs: dict[str, Any]) -> dict[str, float]:
    market = obs.get("market", {}) if isinstance(obs.get("market"), dict) else {}
    prices = market.get("prices", {}) if isinstance(market.get("prices"), dict) else {}
    return {str(key): float(value or 0.0) for key, value in prices.items()}


def _inventory(obs: dict[str, Any]) -> dict[str, float]:
    private = obs.get("private", {}) if isinstance(obs.get("private"), dict) else {}
    totals: dict[str, float] = {}
    shed = private.get("shed", {}) if isinstance(private.get("shed"), dict) else {}
    for key, value in shed.items():
        totals[str(key)] = totals.get(str(key), 0.0) + float(value or 0.0)
    inventories = private.get("inventories", [])
    if isinstance(inventories, list):
        for inventory in inventories:
            if not isinstance(inventory, dict):
                continue
            for key, value in inventory.items():
                totals[str(key)] = totals.get(str(key), 0.0) + float(value or 0.0)
    return totals


def _milk_sell_qty(action: Any) -> float:
    if not isinstance(action, dict):
        return 0.0
    total = 0.0
    for order in action.get("market", []) or []:
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL" and order[1] == PRODUCT:
            total += float(order[2] or 0.0)
    return total


def _remove_milk_sells(action: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(action)
    market = []
    for order in copied.get("market", []) or []:
        if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL" and order[1] == PRODUCT:
            continue
        market.append(order)
    copied["market"] = market
    return copied


def _append_milk_sell(action: dict[str, Any], qty: float) -> bool:
    market = list(action.get("market", []) or [])
    if len(market) >= 10:
        return False
    market.append(["SELL", PRODUCT, qty])
    action["market"] = market
    return True


def _open_loop(actions: list[Any]):
    def agent(observation, configuration=None):
        step = int(observation.get("step", 0)) if isinstance(observation, dict) else 0
        if 0 <= step < len(actions):
            return copy.deepcopy(actions[step])
        return {"farmer": ["PASS"], "hands": [], "market": []}

    return agent


def _terminal_mcv(steps: list[Any], player: int = 0) -> float:
    if not steps:
        return 0.0
    entry = steps[-1][player] if isinstance(steps[-1], list) and len(steps[-1]) > player else {}
    return float(_farm(_obs(entry), player).get("money", 0.0) or 0.0)


def _covered_milk_value(steps: list[Any], player: int = 0) -> dict[str, float]:
    covered_value = 0.0
    attempted_value = 0.0
    covered_units = 0.0
    attempted_units = 0.0
    shortfall_units = 0.0
    weighted_prices = []
    for step in steps:
        if not isinstance(step, list) or len(step) <= player:
            continue
        entry = step[player]
        obs = _obs(entry)
        action = entry.get("action", {}) if isinstance(entry, dict) else {}
        qty = _milk_sell_qty(action)
        if qty <= 0:
            continue
        inventory = _inventory(obs).get(PRODUCT, 0.0)
        price = _prices(obs).get(PRODUCT, 0.0)
        covered = min(qty, inventory)
        attempted_units += qty
        covered_units += covered
        shortfall_units += max(0.0, qty - inventory)
        attempted_value += qty * price
        covered_value += covered * price
        if covered > 0:
            weighted_prices.append((price, covered))
    avg_price = sum(price * units for price, units in weighted_prices) / covered_units if covered_units else 0.0
    return {
        "covered_value": covered_value,
        "attempted_value": attempted_value,
        "covered_units": covered_units,
        "attempted_units": attempted_units,
        "shortfall_units": shortfall_units,
        "weighted_avg_covered_sell_price": avg_price,
    }


def _record_dynamic_traces(candidate_agent) -> list[dict[str, Any]]:
    import kaggle_environments

    source_rows = json.loads(FOUR_OPPONENTS.read_text(encoding="utf-8"))["rows"]
    candidate_rows = [row for row in source_rows if row.get("candidate_side")]
    traces = []
    for index, row in enumerate(candidate_rows):
        seed = int(row["seed"])
        opponent_id = row["opponent"]
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        errors = []
        try:
            env.run([candidate_agent, _opponent(opponent_id, index)])
        except Exception as exc:
            errors.append(repr(exc))
        own_actions = [copy.deepcopy(step[0].get("action", {})) for step in env.steps if isinstance(step, list) and len(step) >= 2]
        opponent_actions = [copy.deepcopy(step[1].get("action", {})) for step in env.steps if isinstance(step, list) and len(step) >= 2]
        price_series = [_prices(_obs(step[0])).get(PRODUCT, 0.0) for step in env.steps if isinstance(step, list) and step]
        traces.append(
            {
                "seed": seed,
                "opponent": opponent_id,
                "dynamic_steps": env.steps,
                "own_actions": own_actions,
                "opponent_actions": opponent_actions,
                "milk_prices": price_series,
                "dynamic_terminal_mcv": _terminal_mcv(env.steps, 0),
                "completed": len(env.steps) == 720 and not errors,
                "errors": errors,
            }
        )
    return traces


def _high_price_threshold() -> float:
    if MARKET_TIMING.exists():
        data = json.loads(MARKET_TIMING.read_text(encoding="utf-8"))
        milk = data["summary"]["product_summary_by_group"]["high"][PRODUCT]
        return float(milk["mean_weighted_avg_sell_price"])
    return 175.0


def _shift_milk_sells(actions: list[Any], prices: list[float], threshold: float) -> tuple[list[Any], dict[str, Any]]:
    modified = [copy.deepcopy(action) for action in actions]
    shifts = []
    blocked = []
    for step, action in enumerate(actions):
        qty = _milk_sell_qty(action)
        if qty <= 0:
            continue
        price = prices[step] if step < len(prices) else 0.0
        if price >= threshold:
            continue
        target = next((future for future in range(step + 1, len(prices)) if prices[future] >= threshold), None)
        if target is None:
            blocked.append({"from_step": step, "qty": qty, "from_price": price, "reason": "no_future_high_price_window"})
            continue
        candidate_action = _remove_milk_sells(modified[step])
        target_action = copy.deepcopy(modified[target])
        if not _append_milk_sell(target_action, qty):
            blocked.append({"from_step": step, "to_step": target, "qty": qty, "from_price": price, "to_price": prices[target], "reason": "target_market_order_cap"})
            continue
        modified[step] = candidate_action
        modified[target] = target_action
        shifts.append({"from_step": step, "to_step": target, "qty": qty, "from_price": price, "to_price": prices[target]})
    return modified, {"shift_count": len(shifts), "shifted_qty": sum(item["qty"] for item in shifts), "shifts": shifts, "blocked": blocked}


def _run_open_loop(seed: int, own_actions: list[Any], opponent_actions: list[Any]) -> tuple[list[Any], list[str]]:
    import kaggle_environments

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    errors = []
    try:
        env.run([_open_loop(own_actions), _open_loop(opponent_actions)])
    except Exception as exc:
        errors.append(repr(exc))
    return env.steps, errors


class DelayedMilkSellWrapper:
    def __init__(self, base_agent, threshold: float):
        self.base_agent = base_agent
        self.threshold = threshold
        self.pending_qty = 0.0
        self.removed_events: list[dict[str, Any]] = []
        self.release_events: list[dict[str, Any]] = []
        self.blocked_release_steps = 0

    def __call__(self, observation, configuration=None):
        action = copy.deepcopy(self.base_agent(observation, configuration))
        if not isinstance(action, dict):
            return action
        step = int(observation.get("step", 0)) if isinstance(observation, dict) else 0
        day = int(observation.get("day", 0)) if isinstance(observation, dict) else 0
        hour = int(observation.get("hour", 0)) if isinstance(observation, dict) else 0
        price = _prices(observation).get(PRODUCT, 0.0) if isinstance(observation, dict) else 0.0
        milk_qty = _milk_sell_qty(action)
        if milk_qty > 0 and price < self.threshold:
            action = _remove_milk_sells(action)
            self.pending_qty += milk_qty
            self.removed_events.append(
                {"step": step, "day": day, "hour": hour, "qty": milk_qty, "price": price}
            )
        if self.pending_qty > 0 and price >= self.threshold:
            qty = self.pending_qty
            if _append_milk_sell(action, qty):
                self.pending_qty = 0.0
                self.release_events.append(
                    {"step": step, "day": day, "hour": hour, "qty": qty, "price": price}
                )
            else:
                self.blocked_release_steps += 1
        return action


def _run_dynamic_pair(package_dir: Path, seed: int, opponent_id: str, index: int, threshold: float) -> dict[str, Any]:
    import kaggle_environments

    baseline_candidate = _load(package_dir / "APEX4_PPO_FINAL_SINGLE.py", f"milk_pair_base_{seed}_{index}")
    counter_candidate = _load(package_dir / "APEX4_PPO_FINAL_SINGLE.py", f"milk_pair_counter_{seed}_{index}")
    baseline_env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    counter_env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    baseline_errors = []
    counter_errors = []
    try:
        baseline_env.run([baseline_candidate.agent, _opponent(opponent_id, index * 2)])
    except Exception as exc:
        baseline_errors.append(repr(exc))
    wrapper = DelayedMilkSellWrapper(counter_candidate.agent, threshold)
    try:
        counter_env.run([wrapper, _opponent(opponent_id, index * 2 + 1)])
    except Exception as exc:
        counter_errors.append(repr(exc))
    baseline_mcv = _terminal_mcv(baseline_env.steps, 0)
    counter_mcv = _terminal_mcv(counter_env.steps, 0)
    return {
        "seed": seed,
        "opponent": opponent_id,
        "group": "low" if baseline_mcv < 60000 else "high" if baseline_mcv >= 100000 else "middle",
        "baseline_terminal_mcv": baseline_mcv,
        "counterfactual_terminal_mcv": counter_mcv,
        "counterfactual_delta_mcv": counter_mcv - baseline_mcv,
        "baseline_milk": _covered_milk_value(baseline_env.steps, 0),
        "counterfactual_milk": _covered_milk_value(counter_env.steps, 0),
        "removed_events": wrapper.removed_events,
        "release_events": wrapper.release_events,
        "pending_qty_terminal": wrapper.pending_qty,
        "blocked_release_steps": wrapper.blocked_release_steps,
        "completed": len(baseline_env.steps) == 720 and len(counter_env.steps) == 720 and not baseline_errors and not counter_errors,
        "errors": {"baseline": baseline_errors, "counterfactual": counter_errors},
    }


def _run_dynamic_wrapper_pairs(package_dir: Path, threshold: float) -> list[dict[str, Any]]:
    source_rows = json.loads(FOUR_OPPONENTS.read_text(encoding="utf-8"))["rows"]
    candidate_rows = [row for row in source_rows if row.get("candidate_side")]
    return [
        _run_dynamic_pair(package_dir, int(row["seed"]), row["opponent"], index, threshold)
        for index, row in enumerate(candidate_rows)
    ]


def _evaluate_trace(trace: dict[str, Any], threshold: float) -> dict[str, Any]:
    baseline_steps, baseline_errors = _run_open_loop(trace["seed"], trace["own_actions"], trace["opponent_actions"])
    shifted_actions, plan = _shift_milk_sells(trace["own_actions"], trace["milk_prices"], threshold)
    counter_steps, counter_errors = _run_open_loop(trace["seed"], shifted_actions, trace["opponent_actions"])
    baseline_mcv = _terminal_mcv(baseline_steps, 0)
    counter_mcv = _terminal_mcv(counter_steps, 0)
    return {
        "seed": trace["seed"],
        "opponent": trace["opponent"],
        "group": "low" if trace["dynamic_terminal_mcv"] < 60000 else "high" if trace["dynamic_terminal_mcv"] >= 100000 else "middle",
        "dynamic_terminal_mcv": trace["dynamic_terminal_mcv"],
        "baseline_open_loop_terminal_mcv": baseline_mcv,
        "counterfactual_terminal_mcv": counter_mcv,
        "counterfactual_delta_mcv": counter_mcv - baseline_mcv,
        "open_loop_reproduces_dynamic": abs(baseline_mcv - trace["dynamic_terminal_mcv"]) <= 1e-6,
        "baseline_milk": _covered_milk_value(baseline_steps, 0),
        "counterfactual_milk": _covered_milk_value(counter_steps, 0),
        "plan": plan,
        "completed": len(baseline_steps) == 720 and len(counter_steps) == 720 and not baseline_errors and not counter_errors,
        "errors": {"dynamic": trace["errors"], "baseline_open_loop": baseline_errors, "counterfactual": counter_errors},
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return {
        "episodes": len(rows),
        "mean_dynamic_terminal_mcv": mean(row["dynamic_terminal_mcv"] for row in rows),
        "mean_baseline_open_loop_terminal_mcv": mean(row["baseline_open_loop_terminal_mcv"] for row in rows),
        "mean_counterfactual_terminal_mcv": mean(row["counterfactual_terminal_mcv"] for row in rows),
        "mean_delta_mcv": mean(row["counterfactual_delta_mcv"] for row in rows),
        "min_delta_mcv": min(row["counterfactual_delta_mcv"] for row in rows),
        "max_delta_mcv": max(row["counterfactual_delta_mcv"] for row in rows),
        "positive_deltas": sum(1 for row in rows if row["counterfactual_delta_mcv"] > 0),
        "negative_deltas": sum(1 for row in rows if row["counterfactual_delta_mcv"] < 0),
        "mean_shifted_qty": mean(row["plan"]["shifted_qty"] for row in rows),
        "mean_shift_count": mean(row["plan"]["shift_count"] for row in rows),
        "open_loop_reproduction_passes": sum(1 for row in rows if row["open_loop_reproduces_dynamic"]),
        "completed": sum(1 for row in rows if row["completed"]),
    }


def _aggregate_dynamic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return {
        "episodes": len(rows),
        "mean_baseline_terminal_mcv": mean(row["baseline_terminal_mcv"] for row in rows),
        "mean_counterfactual_terminal_mcv": mean(row["counterfactual_terminal_mcv"] for row in rows),
        "mean_delta_mcv": mean(row["counterfactual_delta_mcv"] for row in rows),
        "min_delta_mcv": min(row["counterfactual_delta_mcv"] for row in rows),
        "max_delta_mcv": max(row["counterfactual_delta_mcv"] for row in rows),
        "positive_deltas": sum(1 for row in rows if row["counterfactual_delta_mcv"] > 0),
        "negative_deltas": sum(1 for row in rows if row["counterfactual_delta_mcv"] < 0),
        "mean_removed_qty": mean(sum(event["qty"] for event in row["removed_events"]) for row in rows),
        "mean_released_qty": mean(sum(event["qty"] for event in row["release_events"]) for row in rows),
        "mean_pending_qty_terminal": mean(row["pending_qty_terminal"] for row in rows),
        "mean_baseline_milk_value": mean(row["baseline_milk"]["covered_value"] for row in rows),
        "mean_counterfactual_milk_value": mean(row["counterfactual_milk"]["covered_value"] for row in rows),
        "mean_milk_value_delta": mean(row["counterfactual_milk"]["covered_value"] - row["baseline_milk"]["covered_value"] for row in rows),
        "completed": sum(1 for row in rows if row["completed"]),
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["dynamic_wrapper_summary_by_group"]
    low = summary["low"]
    middle = summary["middle"]
    high = summary["high"]
    lines = [
        "# Milk Sell-Timing Counterfactual",
        "",
        "Scope guard: diagnostic only. The frozen PPO package was rerun unchanged. The counterfactual arm wraps the candidate at runtime and changes only MILK sell timing: low-price MILK sells are held and released at the next observed high-price milk window. No checkpoint, single-file submission, v18 engine, Land #4 logic, reward logic, production file, training, or optimization was modified.",
        "",
        f"High-price threshold: `{report['milk_high_price_threshold']:.2f}`",
        "",
        "Open-loop replay note: the stricter open-loop baseline did not reproduce dynamic terminal MCV, so it is retained in JSON only as a failed validity check and is not used for the causal verdict.",
        "",
        "| Group | Episodes | Baseline MCV | Counterfactual MCV | Delta MCV | Positive | Negative | Removed qty | Released qty |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in (("low", low), ("middle", middle), ("high", high)):
        if not item:
            lines.append(f"| {name} | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {name} | {item['episodes']} | {item['mean_baseline_terminal_mcv']:.1f} | "
            f"{item['mean_counterfactual_terminal_mcv']:.1f} | {item['mean_delta_mcv']:.1f} | "
            f"{item['positive_deltas']} | {item['negative_deltas']} | {item['mean_removed_qty']:.1f} | "
            f"{item['mean_released_qty']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Low-Cohort Rows",
            "",
            "| Seed | Opponent | Baseline | Counterfactual | Delta | Shift count | Shifted qty | Baseline milk value | Counter milk value |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in [item for item in report["rows"] if item["group"] == "low"]:
        lines.append(
            f"| {row['seed']} | {row['opponent']} | {row['baseline_terminal_mcv']:.0f} | "
            f"{row['counterfactual_terminal_mcv']:.0f} | {row['counterfactual_delta_mcv']:.0f} | "
            f"{len(row['removed_events'])} | {sum(event['qty'] for event in row['removed_events']):.1f} | "
            f"{row['baseline_milk']['covered_value']:.0f} | {row['counterfactual_milk']['covered_value']:.0f} |"
        )
    lines.extend(
        [
            "",
            "## Causal Read",
            "",
            "This counterfactual is a runtime wrapper, not an implementation. It preserves the frozen candidate code and changes only emitted MILK sell orders during the diagnostic run. A positive delta means delayed milk realization helped terminal MCV in paired seed/opponent evaluation; a negative delta means delayed milk cash disrupted downstream value or missed realized opportunities.",
        ]
    )
    if low:
        lines.append(
            f"Low-cohort mean delta is `{low['mean_delta_mcv']:.1f}` versus the observed low-to-high MCV gap of about `76411.5`."
        )
        if low["mean_delta_mcv"] > 10000:
            lines.append("Verdict: milk timing alone appears to explain a material part of the low-MCV gap.")
        else:
            lines.append("Verdict: milk timing alone does not recover a material part of the low-MCV gap under this conservative replay counterfactual.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    threshold = _high_price_threshold()
    with tempfile.TemporaryDirectory(prefix="milk_sell_cf_pkg_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(package_dir)
        candidate = _load(package_dir / "APEX4_PPO_FINAL_SINGLE.py", "milk_cf_candidate")
        traces = _record_dynamic_traces(candidate.agent)
        open_loop_rows = [_evaluate_trace(trace, threshold) for trace in traces]
        dynamic_rows = _run_dynamic_wrapper_pairs(package_dir, threshold)
    open_loop_summary_by_group = {
        group: _aggregate([row for row in open_loop_rows if row["group"] == group])
        for group in ("low", "middle", "high")
    }
    dynamic_wrapper_summary_by_group = {
        group: _aggregate_dynamic([row for row in dynamic_rows if row["group"] == group])
        for group in ("low", "middle", "high")
    }
    report = {
        "status": "PASS" if all(row["completed"] for row in dynamic_rows) else "FAIL",
        "scope": "diagnostic-only paired milk sell-timing counterfactual",
        "package": str(PACKAGE.relative_to(PROJECT_ROOT)),
        "milk_high_price_threshold": threshold,
        "counterfactual_rule": "runtime wrapper removes emitted low-price MILK sell orders, holds the same quantity pending, and appends it at a later step when milk price >= threshold if the market list has fewer than 10 orders",
        "dynamic_wrapper_summary_by_group": dynamic_wrapper_summary_by_group,
        "rows": dynamic_rows,
        "open_loop_validity_check": {
            "summary_by_group": open_loop_summary_by_group,
            "rows": open_loop_rows,
            "valid_for_causal_verdict": False,
            "reason": "baseline open-loop action replay did not reproduce the frozen dynamic terminal MCV",
        },
    }
    json_path = OUT / "milk_sell_counterfactual.json"
    md_path = OUT / "MILK_SELL_COUNTERFACTUAL.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"status": report["status"], "milk_high_price_threshold": threshold, "dynamic_wrapper_summary_by_group": dynamic_wrapper_summary_by_group}, indent=2))
    print(f"WROTE {json_path}")
    print(f"WROTE {md_path}")


if __name__ == "__main__":
    main()
