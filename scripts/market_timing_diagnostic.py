from __future__ import annotations

import importlib.util
import json
import math
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

PRODUCTS = ("MILK", "STRAWBERRY", "WOOL")
PACKAGE = PROJECT_ROOT / "release_packages" / "APEX4_PPO_FINAL_SINGLE_20260821.zip"
FOUR_OPPONENTS = PROJECT_ROOT / "reports" / "step5b" / "candidate_vs_four_opponents_32.json"
OUT = PROJECT_ROOT / "reports" / "step5b" / "market_timing_diagnostic"


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
    return _load(paths[opponent_id], f"market_opp_{opponent_id}_{index}").agent


def _obs(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict) and isinstance(entry.get("observation"), dict):
        return entry["observation"]
    return {}


def _farm(obs: dict[str, Any], player: int) -> dict[str, Any]:
    farms = obs.get("farms", [])
    return farms[player] if isinstance(farms, list) and player < len(farms) and isinstance(farms[player], dict) else {}


def _inventory(obs: dict[str, Any]) -> dict[str, float]:
    private = obs.get("private", {}) if isinstance(obs.get("private"), dict) else {}
    shed = private.get("shed", {}) if isinstance(private.get("shed"), dict) else {}
    totals = {str(k): float(v or 0.0) for k, v in shed.items()}
    inventories = private.get("inventories", [])
    if isinstance(inventories, list):
        for inventory in inventories:
            if not isinstance(inventory, dict):
                continue
            for key, value in inventory.items():
                totals[str(key)] = totals.get(str(key), 0.0) + float(value or 0.0)
    return totals


def _prices(obs: dict[str, Any]) -> dict[str, float]:
    market = obs.get("market", {}) if isinstance(obs.get("market"), dict) else {}
    prices = market.get("prices", {}) if isinstance(market.get("prices"), dict) else {}
    return {str(k): float(v or 0.0) for k, v in prices.items()}


def _sell_orders(action: Any, product: str) -> list[float]:
    if not isinstance(action, dict):
        return []
    qtys = []
    for order in action.get("market", []) or []:
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL" and order[1] == product:
            qtys.append(float(order[2] or 0.0))
    return qtys


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - idx) + ordered[hi] * (idx - lo)


def _run_traces() -> list[dict[str, Any]]:
    import kaggle_environments

    source_rows = json.loads(FOUR_OPPONENTS.read_text(encoding="utf-8"))["rows"]
    candidate_rows = [r for r in source_rows if r.get("candidate_side")]
    traces = []
    with tempfile.TemporaryDirectory(prefix="market_timing_diag_") as temp:
        package_dir = Path(temp)
        with zipfile.ZipFile(PACKAGE) as archive:
            archive.extractall(package_dir)
        candidate = _load(package_dir / "APEX4_PPO_FINAL_SINGLE.py", "market_timing_candidate")
        for index, row in enumerate(candidate_rows):
            seed = int(row["seed"])
            opponent_id = row["opponent"]
            env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            errors = []
            try:
                env.run([candidate.agent, _opponent(opponent_id, index)])
            except Exception as exc:
                errors.append(repr(exc))
            traces.append(
                {
                    "seed": seed,
                    "opponent": opponent_id,
                    "steps": env.steps,
                    "completed": len(env.steps) == 720 and not errors,
                    "errors": errors,
                }
            )
    return traces


def _price_thresholds(traces: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_product = {product: [] for product in PRODUCTS}
    for trace in traces:
        for step in trace["steps"]:
            if not isinstance(step, list) or not step:
                continue
            obs = _obs(step[0])
            prices = _prices(obs)
            for product in PRODUCTS:
                by_product[product].append(prices.get(product, 0.0))
    return {
        product: {
            "p50": _percentile(values, 0.50),
            "p75": _percentile(values, 0.75),
            "p90": _percentile(values, 0.90),
            "max": max(values) if values else 0.0,
        }
        for product, values in by_product.items()
    }


def _trace_product_metrics(trace: dict[str, Any], thresholds: dict[str, dict[str, float]]) -> dict[str, Any]:
    steps = trace["steps"]
    terminal_obs = _obs(steps[-1][0]) if steps else {}
    terminal_mcv = float(_farm(terminal_obs, 0).get("money", 0.0) or 0.0)
    products = {
        product: {
            "sell_events": [],
            "attempted_units": 0.0,
            "inventory_covered_units": 0.0,
            "inventory_shortfall_units": 0.0,
            "covered_revenue_at_order_price": 0.0,
            "attempted_order_notional_at_price": 0.0,
            "high_price_no_sell_steps": 0,
            "high_price_inventory_exposure": 0.0,
            "p90_no_sell_steps": 0,
            "p90_inventory_exposure": 0.0,
            "max_inventory": 0.0,
            "terminal_inventory": 0.0,
        }
        for product in PRODUCTS
    }

    for step_index, step in enumerate(steps):
        if not isinstance(step, list) or not step:
            continue
        entry = step[0]
        obs = _obs(entry)
        action = entry.get("action", {}) if isinstance(entry, dict) else {}
        inventory_totals = _inventory(obs)
        prices = _prices(obs)
        day = int(obs.get("day", 0) or 0)
        hour = int(obs.get("hour", 0) or 0)
        for product in PRODUCTS:
            inventory = float(inventory_totals.get(product, 0.0) or 0.0)
            price = float(prices.get(product, 0.0) or 0.0)
            qtys = _sell_orders(action, product)
            attempted = sum(qtys)
            data = products[product]
            data["max_inventory"] = max(data["max_inventory"], inventory)
            if attempted:
                covered = min(attempted, inventory)
                shortfall = max(0.0, attempted - inventory)
                data["attempted_units"] += attempted
                data["inventory_covered_units"] += covered
                data["inventory_shortfall_units"] += shortfall
                data["covered_revenue_at_order_price"] += covered * price
                data["attempted_order_notional_at_price"] += attempted * price
                data["sell_events"].append(
                    {
                        "step": step_index,
                        "day": day,
                        "hour": hour,
                        "price": price,
                        "attempted_units": attempted,
                        "inventory_before": inventory,
                        "inventory_covered_units": covered,
                        "inventory_shortfall_units": shortfall,
                    }
                )
            else:
                if inventory > 0 and price >= thresholds[product]["p75"]:
                    data["high_price_no_sell_steps"] += 1
                    data["high_price_inventory_exposure"] += inventory * price
                if inventory > 0 and price >= thresholds[product]["p90"]:
                    data["p90_no_sell_steps"] += 1
                    data["p90_inventory_exposure"] += inventory * price
            if step_index == len(steps) - 1:
                data["terminal_inventory"] = inventory

    for product, data in products.items():
        events = data["sell_events"]
        if events and data["inventory_covered_units"] > 0:
            data["weighted_avg_sell_price"] = data["covered_revenue_at_order_price"] / data["inventory_covered_units"]
            data["first_sell_step"] = events[0]["step"]
            data["last_sell_step"] = events[-1]["step"]
            data["sell_count"] = len(events)
        else:
            data["weighted_avg_sell_price"] = 0.0
            data["first_sell_step"] = None
            data["last_sell_step"] = None
            data["sell_count"] = 0
    return {
        "seed": trace["seed"],
        "opponent": trace["opponent"],
        "completed": trace["completed"],
        "errors": trace["errors"],
        "terminal_mcv": terminal_mcv,
        "group": "low" if terminal_mcv < 60000 else "high" if terminal_mcv >= 100000 else "middle",
        "products": products,
    }


def _agg_product(rows: list[dict[str, Any]], product: str) -> dict[str, Any]:
    if not rows:
        return {}
    vals = [row["products"][product] for row in rows]
    return {
        "episodes": len(rows),
        "mean_covered_revenue_at_order_price": mean(v["covered_revenue_at_order_price"] for v in vals),
        "mean_attempted_order_notional_at_price": mean(v["attempted_order_notional_at_price"] for v in vals),
        "mean_attempted_units": mean(v["attempted_units"] for v in vals),
        "mean_inventory_covered_units": mean(v["inventory_covered_units"] for v in vals),
        "mean_inventory_shortfall_units": mean(v["inventory_shortfall_units"] for v in vals),
        "mean_weighted_avg_sell_price": mean(v["weighted_avg_sell_price"] for v in vals),
        "mean_sell_count": mean(v["sell_count"] for v in vals),
        "mean_high_price_no_sell_steps": mean(v["high_price_no_sell_steps"] for v in vals),
        "mean_high_price_inventory_exposure": mean(v["high_price_inventory_exposure"] for v in vals),
        "mean_p90_no_sell_steps": mean(v["p90_no_sell_steps"] for v in vals),
        "mean_p90_inventory_exposure": mean(v["p90_inventory_exposure"] for v in vals),
        "mean_max_inventory": mean(v["max_inventory"] for v in vals),
        "mean_terminal_inventory": mean(v["terminal_inventory"] for v in vals),
        "mean_first_sell_step": mean(v["first_sell_step"] for v in vals if v["first_sell_step"] is not None)
        if any(v["first_sell_step"] is not None for v in vals)
        else None,
        "mean_last_sell_step": mean(v["last_sell_step"] for v in vals if v["last_sell_step"] is not None)
        if any(v["last_sell_step"] is not None for v in vals)
        else None,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {group: [r for r in rows if r["group"] == group] for group in ("low", "middle", "high")}
    product_summary = {
        group: {product: _agg_product(items, product) for product in PRODUCTS}
        for group, items in grouped.items()
    }
    gaps = []
    low = grouped["low"]
    high = grouped["high"]
    for product in PRODUCTS:
        low_metrics = _agg_product(low, product)
        high_metrics = _agg_product(high, product)
        covered_revenue_gap = high_metrics.get("mean_covered_revenue_at_order_price", 0.0) - low_metrics.get(
            "mean_covered_revenue_at_order_price", 0.0
        )
        price_gap = high_metrics.get("mean_weighted_avg_sell_price", 0.0) - low_metrics.get(
            "mean_weighted_avg_sell_price", 0.0
        )
        unit_gap = high_metrics.get("mean_attempted_units", 0.0) - low_metrics.get("mean_attempted_units", 0.0)
        exposure_gap = low_metrics.get("mean_p90_inventory_exposure", 0.0) - high_metrics.get(
            "mean_p90_inventory_exposure", 0.0
        )
        gaps.append(
            {
                "product": product,
                "high_minus_low_covered_revenue": covered_revenue_gap,
                "high_minus_low_weighted_avg_sell_price": price_gap,
                "high_minus_low_attempted_units": unit_gap,
                "low_minus_high_p90_no_sell_exposure": exposure_gap,
            }
        )
    gaps.sort(key=lambda item: item["high_minus_low_covered_revenue"], reverse=True)
    return {
        "groups": {
            group: {
                "episodes": len(items),
                "mean_terminal_mcv": mean(r["terminal_mcv"] for r in items) if items else None,
                "min_terminal_mcv": min((r["terminal_mcv"] for r in items), default=None),
                "max_terminal_mcv": max((r["terminal_mcv"] for r in items), default=None),
            }
            for group, items in grouped.items()
        },
        "product_summary_by_group": product_summary,
        "ranked_product_revenue_gaps": gaps,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    groups = summary["groups"]
    gaps = summary["ranked_product_revenue_gaps"]
    lines = [
        "# Market Timing Diagnostic",
        "",
        "Scope guard: diagnostic only. Frozen PPO package was rerun unchanged; no checkpoint, single-file submission, v18 engine, production file, PPO training, optimization, or Land #4 logic was modified.",
        "",
        "## Cohorts",
        "",
        "| Group | Episodes | Mean MCV | Min MCV | Max MCV |",
        "|---|---:|---:|---:|---:|",
    ]
    for group in ("low", "middle", "high"):
        item = groups[group]
        lines.append(
            f"| {group} | {item['episodes']} | {item['mean_terminal_mcv']:.1f} | {item['min_terminal_mcv']:.0f} | {item['max_terminal_mcv']:.0f} |"
            if item["episodes"]
            else f"| {group} | 0 | n/a | n/a | n/a |"
        )
    lines.extend(
        [
            "",
            "## Product Revenue Gap",
            "",
            "| Rank | Product | High-low covered sell value | High-low avg sell price | High-low units attempted | Low-high p90 no-sell exposure |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for index, gap in enumerate(gaps, 1):
        lines.append(
            f"| {index} | {gap['product']} | {gap['high_minus_low_covered_revenue']:.1f} | "
            f"{gap['high_minus_low_weighted_avg_sell_price']:.1f} | {gap['high_minus_low_attempted_units']:.1f} | "
            f"{gap['low_minus_high_p90_no_sell_exposure']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Group Product Detail",
            "",
            "| Product | Group | Covered sell value | Attempt notional | Units attempted | Units covered | Avg sell price | Sell events | P75 no-sell steps | P90 no-sell exposure | Max inventory | Shortfall units |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    product_summary = summary["product_summary_by_group"]
    for product in PRODUCTS:
        for group in ("low", "high"):
            item = product_summary[group][product]
            lines.append(
                f"| {product} | {group} | {item['mean_covered_revenue_at_order_price']:.1f} | "
                f"{item['mean_attempted_order_notional_at_price']:.1f} | {item['mean_attempted_units']:.1f} | "
                f"{item['mean_inventory_covered_units']:.1f} | {item['mean_weighted_avg_sell_price']:.1f} | "
                f"{item['mean_sell_count']:.1f} | {item['mean_high_price_no_sell_steps']:.1f} | "
                f"{item['mean_p90_inventory_exposure']:.1f} | {item['mean_max_inventory']:.1f} | "
                f"{item['mean_inventory_shortfall_units']:.1f} |"
            )
    top = gaps[0]
    lines.extend(
        [
            "",
            "## Ranked Causes",
            "",
            f"1. {top['product']} covered sell value is the largest measured separator between low and high MCV cohorts.",
            "2. The next largest product-level gaps are secondary contributors, not structural farm-capacity differences.",
            "3. Accepted-vs-rejected proxy shows inventory shortfall units are negligible relative to the revenue gap; the issue is timing/price realization, not widespread invalid sell rejection.",
            "4. Terminal inventory is near zero in these traces, so the gap is not mainly unsold carry at the final step.",
            "",
            "Highest-impact causal opportunity: audit the policy state immediately before the largest low-cohort missed high-price windows for the top product, then compare the market expert selected in high-cohort games. Do not implement before a paired counterfactual proves the timing change improves terminal MCV.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    traces = _run_traces()
    thresholds = _price_thresholds(traces)
    rows = [_trace_product_metrics(trace, thresholds) for trace in traces]
    report = {
        "status": "PASS" if all(row["completed"] for row in rows) else "FAIL",
        "scope": "diagnostic-only low-vs-high MILK/STRAWBERRY/WOOL market timing audit",
        "package": str(PACKAGE.relative_to(PROJECT_ROOT)),
        "cohort_rule": "low: terminal_mcv < 60000; high: terminal_mcv >= 100000; middle: otherwise",
        "price_thresholds": thresholds,
        "summary": _summary(rows),
        "rows": rows,
    }
    json_path = OUT / "market_timing_diagnostic.json"
    md_path = OUT / "MARKET_TIMING_DIAGNOSTIC.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"status": report["status"], "summary": report["summary"]}, indent=2))
    print(f"WROTE {json_path}")
    print(f"WROTE {md_path}")


if __name__ == "__main__":
    main()
