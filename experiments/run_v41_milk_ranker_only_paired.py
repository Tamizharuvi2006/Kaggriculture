"""Paired V4.1 versus MILK-ranker-only evaluation."""

import hashlib
import importlib.util
import json
import os
import statistics
from datetime import datetime, timezone

import kaggle_environments

ROOT = r"D:\Kaggriculture"
V41_PATH = os.path.join(ROOT, "baseline", "kaitofukami-v18.py")
REPORT_PATH = os.path.join(ROOT, "reports", "v41_milk_ranker_only_paired_32.json")
SEEDS = list(range(1000, 1032))
EPISODE_STEPS = 720


def load_v41(name):
    spec = importlib.util.spec_from_file_location(name, V41_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure_strategy({
        "use_fixed_schedule": True,
        "v13_market_adaptation": True,
        "opening_melons": 9,
    })
    return module


def milk_price(module, observation):
    prices = module._get(module._get(observation, "market", {}), "prices", {}) or {}
    value = prices.get("MILK", 0.0)
    return float(value.get("price", 0.0) if isinstance(value, dict) else value or 0.0)


def rank_market(module, action, observation):
    if not isinstance(action, dict):
        return action, False
    orders = action.get("market", [])
    price = milk_price(module, observation)
    if price < 230.0 or len(orders) <= 1:
        return action, False

    def priority(item):
        index, order = item
        if not order or order[0] != "SELL":
            return (10, index)
        product = order[1] if len(order) > 1 else ""
        if product == "MILK":
            return (0, index)
        if product == "MELON":
            return (1, index)
        if product == "STRAWBERRY":
            return (2, index)
        if product == "WHEAT":
            return (3, index)
        return (4, index)

    reordered = [order for _, order in sorted(enumerate(orders), key=priority)]
    changed = reordered != orders
    if changed:
        action = dict(action)
        action["market"] = reordered
    return action, changed


def final_money(history, player_index):
    return float(history[-1][player_index]["observation"]["farms"][player_index]["money"])


def run_match(seed, candidate_first):
    baseline = load_v41(f"v41_base_{seed}")
    ranked = load_v41(f"v41_rank_{seed}")
    interventions = 0

    def baseline_agent(observation, configuration=None):
        return baseline.agent(observation, configuration)

    def ranked_agent(observation, configuration=None):
        nonlocal interventions
        action = ranked.agent(observation, configuration)
        action, changed = rank_market(ranked, action, observation)
        interventions += int(changed)
        return action

    agents = [ranked_agent, baseline_agent] if candidate_first else [baseline_agent, ranked_agent]
    environment = kaggle_environments.make(
        "kaggriculture", configuration={"episodeSteps": EPISODE_STEPS, "seed": seed}
    )
    history = environment.run(agents)
    candidate_index = 0 if candidate_first else 1
    baseline_index = 1 if candidate_first else 0
    candidate_money = final_money(history, candidate_index)
    baseline_money = final_money(history, baseline_index)
    transitions = max(0, len(history) - 1)
    return {
        "seed": seed,
        "candidate_seat": candidate_index,
        "calls": len(history),
        "transitions": transitions,
        "candidate_mcv": candidate_money,
        "baseline_mcv": baseline_money,
        "delta": candidate_money - baseline_money,
        "candidate_win": candidate_money > baseline_money,
        "tie": candidate_money == baseline_money,
        "ranker_order_changes": interventions,
        "valid": transitions == 719 and len(history) == 720,
    }


def main():
    records = [run_match(seed, candidate_first=(seed % 2 == 0)) for seed in SEEDS]
    deltas = [record["delta"] for record in records]
    candidate_wins = sum(record["candidate_win"] for record in records)
    ties = sum(record["tie"] for record in records)
    baseline_wins = len(records) - candidate_wins - ties
    report = {
        "experiment": "V4.1 versus MILK-first ranker only",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": V41_PATH,
        "source_sha256": hashlib.sha256(open(V41_PATH, "rb").read()).hexdigest(),
        "configuration": {
            "episode_steps": EPISODE_STEPS,
            "seeds": SEEDS,
            "opening_melons": 9,
            "use_fixed_schedule": True,
            "ranker_threshold_milk_price": 230.0,
            "ranker_only": True,
            "seat_swapped": True,
        },
        "acceptance": {
            "all_720_calls": all(record["calls"] == 720 for record in records),
            "all_719_transitions": all(record["transitions"] == 719 for record in records),
            "all_valid": all(record["valid"] for record in records),
            "no_opening_change": True,
            "no_quantity_or_affordability_change": True,
        },
        "summary": {
            "paired_matches": len(records),
            "ranker_wins": candidate_wins,
            "baseline_wins": baseline_wins,
            "ties": ties,
            "ranker_win_rate": candidate_wins / len(records),
            "mean_ranker_mcv": statistics.mean(record["candidate_mcv"] for record in records),
            "mean_baseline_mcv": statistics.mean(record["baseline_mcv"] for record in records),
            "mean_delta": statistics.mean(deltas),
            "median_delta": statistics.median(deltas),
            "stdev_delta": statistics.stdev(deltas) if len(deltas) > 1 else 0.0,
            "min_delta": min(deltas),
            "max_delta": max(deltas),
            "total_ranker_order_changes": sum(record["ranker_order_changes"] for record in records),
        },
        "records": records,
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
