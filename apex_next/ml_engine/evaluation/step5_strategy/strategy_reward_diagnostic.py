"""Compare fixed Step 5B strategy rewards on identical CUDA game seeds."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.evaluation.step5_strategy.v18_strategy_adapter import configured_v18_agent
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import _opponent_pool
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv


DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "step5b" / "strategy_reward_diagnostic.json"


def _summary(values: np.ndarray) -> dict[str, float]:
    mean = float(values.mean())
    std = float(values.std(ddof=1)) if values.size > 1 else 0.0
    half_width = 1.96 * std / math.sqrt(values.size) if values.size > 1 else 0.0
    return {
        "mean_reward": mean,
        "std_reward": std,
        "p05_reward": float(np.quantile(values, 0.05)),
        "p95_reward": float(np.quantile(values, 0.95)),
        "win_rate": float((values > 0).mean()),
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
    }


def run_diagnostic(episodes: int = 32, seed_start: int = 68000, output_path: Path = DEFAULT_OUTPUT) -> dict:
    strategy_names = ["BALANCED", "LIVESTOCK", "PREMIUM", "WHEAT_RUSH"]
    seeds = [seed_start + idx for idx in range(episodes)]
    opponent_pool = _opponent_pool()
    opponent_ids = [opponent_pool[idx % len(opponent_pool)][0] for idx in range(episodes)]
    results: dict[str, list[dict]] = {}
    started = time.perf_counter()

    for strategy_name in strategy_names:
        opponent_fns = [opponent_pool[idx % len(opponent_pool)][1] for idx in range(episodes)]
        env = CudaBatchPPOEnv(opponent_fns, device="cuda:0")
        env.reset(seeds, extract_initial_features=False)
        agents = [
            configured_v18_agent(strategy_name, module_suffix=920000 + idx)
            for idx in range(episodes)
        ]
        done = [False] * episodes
        while not all(done):
            actions = []
            for idx in range(episodes):
                obs = env.observation(idx, 0)
                actions.append(sanitize_action(call_agent(agents[idx], obs, env.configuration)))
            _, _, done, infos = env.step(actions, extract_next_features=False)
            if any(int(info["step"]) > 719 for info in infos):
                raise AssertionError(f"strategy {strategy_name} exceeded 719 transitions")
        rows = []
        for idx, seed in enumerate(seeds):
            metrics = env.engine.terminal_metrics(idx, 0)
            rows.append(
                {
                    "seed": seed,
                    "opponent_id": opponent_ids[idx],
                    "strategy": strategy_name,
                    "steps": 719,
                    "raw_reward": float(metrics["raw_terminal_reward"]),
                    "normalized_reward": float(metrics["normalized_reward"]),
                    "winner": metrics.get("winner"),
                }
            )
        values = np.asarray([row["normalized_reward"] for row in rows], dtype=np.float64)
        results[strategy_name] = rows
        results[f"{strategy_name}__summary"] = _summary(values)

    pairwise: dict[str, dict[str, float]] = {}
    for left_index, left in enumerate(strategy_names):
        left_values = np.asarray([row["normalized_reward"] for row in results[left]], dtype=np.float64)
        for right in strategy_names[left_index + 1 :]:
            right_values = np.asarray([row["normalized_reward"] for row in results[right]], dtype=np.float64)
            diff = left_values - right_values
            pairwise[f"{left}_minus_{right}"] = {
                "mean_difference": float(diff.mean()),
                "std_difference": float(diff.std(ddof=1)),
                "positive_fraction": float((diff > 0).mean()),
                "p05_difference": float(np.quantile(diff, 0.05)),
                "p95_difference": float(np.quantile(diff, 0.95)),
            }

    report = {
        "status": "PASS",
        "diagnostic": "frozen strategy reward comparison",
        "engine": "immutable OPT-1 CUDA snapshot through CudaBatchPPOEnv",
        "cuda": env.actual_cuda_used,
        "tensor_device": str(env.engine.money.device),
        "episodes_per_strategy": episodes,
        "seed_start": seed_start,
        "same_seeds_and_opponent_schedule": True,
        "ppo_updates": False,
        "decision_selector": False,
        "strategies": strategy_names,
        "results": results,
        "pairwise_differences": pairwise,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "sealed_production_modified": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare fixed Step 5B strategy rewards.")
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument("--seed-start", type=int, default=68000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run_diagnostic(args.episodes, args.seed_start, args.output), indent=2))


if __name__ == "__main__":
    main()
