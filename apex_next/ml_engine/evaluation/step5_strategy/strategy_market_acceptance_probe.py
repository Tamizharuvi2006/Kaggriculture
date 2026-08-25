"""Audit early market acceptance and state mutation for fixed strategies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import _configured_apex4_agent, _opponent_pool
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import STRATEGY_PROFILES


def _scalar(value: Any) -> float:
    return float(value.item()) if hasattr(value, "item") else float(value)


def _shed_used(engine: Any, env_idx: int, player_idx: int) -> int:
    return int(sum(engine.private_shed[env_idx][player_idx].values()))


def _state(engine: Any, env_idx: int, player_idx: int) -> dict[str, Any]:
    return {
        "money": _scalar(engine.money_mirror[env_idx][player_idx]),
        "shed_used": _shed_used(engine, env_idx, player_idx),
        "workers": len(engine.hands[env_idx][player_idx]),
        "land": len(engine.unlocked_quadrants[env_idx][player_idx]),
    }


def _reason(engine: Any, env_idx: int, player_idx: int, op: str, item: str, price: float) -> str:
    state = _state(engine, env_idx, player_idx)
    if op == "SELL" and engine.private_shed[env_idx][player_idx].get(item, 0) <= 0:
        return "missing_item_in_shed"
    if op in {"BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"} and state["money"] < price:
        return "insufficient_money"
    if op in {"BUY_PRODUCT", "BUY_ANIMAL"} and state["shed_used"] >= engine.SHED_CAPACITY:
        return "shed_capacity"
    if op == "BUY_PRODUCT" and item not in ("WHEAT", "FERTILIZER"):
        return "unsupported_buy_product"
    if op == "BUY_SEED" and item not in engine.CROP_SEED_COSTS:
        return "unsupported_seed"
    if op == "BUY_ANIMAL" and item not in engine.ANIMAL_COSTS:
        return "unsupported_animal"
    return "accepted_by_precheck"


def _install_audit(engine: Any, audit: list[dict[str, Any]]) -> None:
    original_commit = engine._commit_market_unit
    original_hire = engine._do_hire
    original_land = engine._do_buy_land

    def commit(env_idx: int, player_idx: int, op: str, item: str, price: float) -> bool:
        before = _state(engine, env_idx, player_idx)
        reason = _reason(engine, env_idx, player_idx, op, item, price)
        result = original_commit(env_idx, player_idx, op, item, price)
        after = _state(engine, env_idx, player_idx)
        audit.append({
            "kind": "market_unit",
            "env_idx": env_idx,
            "player_idx": player_idx,
            "op": op,
            "item": item,
            "price": float(price),
            "precheck_reason": reason,
            "accepted": bool(result),
            "mutated_state": before != after,
            "before": before,
            "after": after,
        })
        return result

    def hire(env_idx: int, player_idx: int) -> None:
        before = _state(engine, env_idx, player_idx)
        original_hire(env_idx, player_idx)
        after = _state(engine, env_idx, player_idx)
        audit.append({
            "kind": "hire",
            "env_idx": env_idx,
            "player_idx": player_idx,
            "accepted": before != after,
            "mutated_state": before != after,
            "before": before,
            "after": after,
        })

    def land(env_idx: int, player_idx: int) -> None:
        before = _state(engine, env_idx, player_idx)
        original_land(env_idx, player_idx)
        after = _state(engine, env_idx, player_idx)
        audit.append({
            "kind": "buy_land",
            "env_idx": env_idx,
            "player_idx": player_idx,
            "accepted": before != after,
            "mutated_state": before != after,
            "before": before,
            "after": after,
        })

    engine._commit_market_unit = commit
    engine._do_hire = hire
    engine._do_buy_land = land


def run_probe(episodes: int = 32, seed_start: int = 68000, output_path: Path | None = None) -> dict[str, Any]:
    seeds = [seed_start + idx for idx in range(episodes)]
    opponent_pool = _opponent_pool()
    opponent_ids = [opponent_pool[idx % len(opponent_pool)][0] for idx in range(episodes)]
    results: dict[str, Any] = {}
    for profile_index, profile in enumerate(STRATEGY_PROFILES):
        opponent_fns = [opponent_pool[idx % len(opponent_pool)][1] for idx in range(episodes)]
        env = CudaBatchPPOEnv(opponent_fns, device="cuda:0")
        env.reset(seeds, extract_initial_features=False)
        audit: list[dict[str, Any]] = []
        _install_audit(env.engine, audit)
        agents = [
            _configured_apex4_agent(profile["overrides"], module_suffix=933000 + profile_index * 1000 + idx)
            for idx in range(episodes)
        ]
        action_rows: list[dict[str, Any]] = []
        for step in range(3):
            actions = []
            for idx, agent in enumerate(agents):
                action = sanitize_action(call_agent(agent, env.observation(idx, 0), env.configuration))
                actions.append(action)
                action_rows.append({"seed": seeds[idx], "step": step, "action": action})
            env.step(actions, extract_next_features=False)
        results[profile["name"]] = {
            "actions": action_rows,
            "market_audit": audit,
        }

    report = {
        "status": "PASS",
        "diagnostic": "strategy market acceptance and mutation probe",
        "engine": "immutable OPT-1 CUDA snapshot through CudaBatchPPOEnv",
        "cuda": True,
        "episodes": episodes,
        "seed_start": seed_start,
        "same_seeds_and_opponent_schedule": True,
        "steps_instrumented": 3,
        "opponent_ids": opponent_ids,
        "strategies": [profile["name"] for profile in STRATEGY_PROFILES],
        "results": results,
        "ppo_updates": False,
        "sealed_production_modified": False,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--seed-start", type=int, default=68000)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "step5b" / "strategy_market_acceptance_probe.json")
    args = parser.parse_args()
    print(json.dumps(run_probe(args.episodes, args.seed_start, args.output), indent=2))


if __name__ == "__main__":
    main()
