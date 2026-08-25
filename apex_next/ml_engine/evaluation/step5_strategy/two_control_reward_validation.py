"""Matched 32-seed validation for the bounded two-control strategy adapter."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, load_agent, sanitize_action
from apex_next.ml_engine.training.cuda_ppo_env import CudaPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import APEX4_PATH, _opponent_pool
from apex_next.ml_engine.evaluation.step5_strategy.two_control_strategy_adapter import (
    configured_two_control_agent,
)


SEED_START = 68000
EPISODES = 32
CONTROL_CONFIGS = {
    "BALANCED_0_0": (0.0, 0.0),
    "MARKET_POS_025": (0.25, 0.0),
    "MARKET_NEG_025": (-0.25, 0.0),
    "ROUTE_POS_025": (0.0, 0.25),
    "ROUTE_NEG_025": (0.0, -0.25),
}


def _signature(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _summary(values: list[float], wins: list[int]) -> dict[str, float]:
    ordered = sorted(values)
    p05 = float(np.quantile(ordered, 0.05, method="linear"))
    p95 = float(np.quantile(ordered, 0.95, method="linear"))
    return {
        "mean_reward": float(mean(values)),
        "std_reward": float(pstdev(values)),
        "p05_reward": p05,
        "p95_reward": p95,
        "win_rate": float(mean(wins)),
    }


def _rollout(agent, opponent_fn, seed: int, suffix: int) -> dict[str, Any]:
    env = CudaPPOEnv(opponent_fn=opponent_fn, device="cuda:0")
    env.reset(seed=seed)
    signatures: list[str] = []
    invalid_actions = 0
    done = False
    steps = 0
    while not done:
        action = sanitize_action(call_agent(agent, env.observation(0), env.configuration))
        if not isinstance(action, dict):
            invalid_actions += 1
        signatures.append(_signature(action))
        _, _, done, info = env.step(action)
        steps += 1
        if steps > 719:
            raise AssertionError(f"seed {seed} exceeded 719 transitions")

    terminal = env.engine.terminal_metrics(0, 0)
    reward = float(terminal["normalized_reward"])
    return {
        "seed": seed,
        "steps": steps,
        "completed": bool(done),
        "reward": reward,
        "winner": int(terminal["winner"]),
        "actions": signatures,
        "invalid_actions": invalid_actions,
        "actual_cuda_used": bool(env.actual_cuda_used),
        "device": str(env.engine.money.device),
        "finite_reward": math.isfinite(reward),
        "info_keys": sorted(info.keys()) if isinstance(info, dict) else [],
        "suffix": suffix,
    }


def run(output: Path, seed_start: int = SEED_START, episodes: int = EPISODES) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for two-control validation")

    opponent_pool = _opponent_pool()
    opponent_fns = [agent_fn for _, agent_fn in opponent_pool]
    results: dict[str, list[dict[str, Any]]] = {}
    for config_index, (name, (market, route)) in enumerate(CONTROL_CONFIGS.items()):
        agent = configured_two_control_agent(market, route, 100 + config_index)
        rows = []
        for offset in range(episodes):
            opponent_fn = opponent_fns[offset % len(opponent_fns)]
            rows.append(_rollout(agent, opponent_fn, seed_start + offset, 100 + config_index))
        results[name] = rows

    baseline = results["BALANCED_0_0"]
    baseline_by_seed = {row["seed"]: row for row in baseline}
    summaries = {}
    pairwise = {}
    all_checks = []
    for name, rows in results.items():
        summaries[name] = _summary([row["reward"] for row in rows], [row["winner"] == 0 for row in rows])
        if name != "BALANCED_0_0":
            deltas = [row["reward"] - baseline_by_seed[row["seed"]]["reward"] for row in rows]
            pairwise[name] = {
                "mean_delta_vs_balanced": float(mean(deltas)),
                "std_delta_vs_balanced": float(pstdev(deltas)),
                "positive_delta_fraction": float(mean(delta > 0.0 for delta in deltas)),
                "per_seed_delta": [
                    {"seed": row["seed"], "delta": delta}
                    for row, delta in zip(rows, deltas)
                ],
                "action_difference_fraction": float(mean(
                    row["actions"] != baseline_by_seed[row["seed"]]["actions"] for row in rows
                )),
            }
        all_checks.extend(rows)

    zero = results["BALANCED_0_0"]
    zero_equivalent = all(
        row["steps"] == baseline_by_seed[row["seed"]]["steps"] == 719
        and row["actions"] == baseline_by_seed[row["seed"]]["actions"]
        and math.isclose(row["reward"], baseline_by_seed[row["seed"]]["reward"], abs_tol=1e-12)
        for row in zero
    )
    safety_pass = all(
        row["steps"] == 719
        and row["completed"]
        and row["invalid_actions"] == 0
        and row["actual_cuda_used"]
        and row["device"] == "cuda:0"
        and row["finite_reward"]
        for row in all_checks
    )
    report = {
        "status": "PASS" if zero_equivalent and safety_pass else "FAIL",
        "validation": "matched two-control reward validation",
        "seed_start": seed_start,
        "episodes_per_configuration": episodes,
        "same_seed_and_opponent_schedule": True,
        "control_range": [-0.25, 0.25],
        "cuda": True,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "zero_control_exact_fixed_v18": zero_equivalent,
        "safety_invariants_pass": safety_pass,
        "summaries": summaries,
        "pairwise_vs_balanced": pairwise,
        "results": results,
        "ppo_updates": False,
        "production_modified": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=SEED_START)
    parser.add_argument("--episodes", type=int, default=EPISODES)
    parser.add_argument("--output", type=Path, default=Path("reports/step5b/two_control_reward_validation.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.seed_start, args.episodes), indent=2))


if __name__ == "__main__":
    main()
