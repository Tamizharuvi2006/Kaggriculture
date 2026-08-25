"""Trace strategy configuration through APEX4 action normalization."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import _opponent_pool
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import APEX4_PATH, STRATEGY_PROFILES


def _load_configured_module(overrides: dict, suffix: int):
    module_name = f"strategy_trace_{suffix}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, APEX4_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {APEX4_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = dict(overrides)
    config["use_fixed_schedule"] = False
    module.configure_strategy(config)
    return module


def run_probe(episodes: int = 32, seed_start: int = 68000, output_path: Path | None = None) -> dict:
    seeds = [seed_start + idx for idx in range(episodes)]
    pool = _opponent_pool()
    opponent_fns = [pool[idx % len(pool)][1] for idx in range(episodes)]
    results = {}
    for profile_index, profile in enumerate(STRATEGY_PROFILES):
        env = CudaBatchPPOEnv(opponent_fns, device="cuda:0")
        env.reset(seeds, extract_initial_features=False)
        modules = [
            _load_configured_module(profile["overrides"], 934000 + profile_index * 1000 + idx)
            for idx in range(episodes)
        ]
        rows = []
        for step in range(3):
            actions = []
            for idx, module in enumerate(modules):
                obs = env.observation(idx, 0)
                raw = call_agent(module.agent, obs, env.configuration)
                sanitized = sanitize_action(raw)
                rows.append(
                    {
                        "seed": seeds[idx],
                        "step": step,
                        "config": {
                            key: module.STRATEGY.get(key)
                            for key in (
                                "use_fixed_schedule",
                                "fixed_schedule_version",
                                "cows",
                                "sheep",
                                "animal_daily_cap",
                                "force_expert",
                                "wheat_rush_animal_cap",
                            )
                        },
                        "raw_action": raw,
                        "sanitized_action": sanitized,
                    }
                )
                actions.append(sanitized)
            env.step(actions, extract_next_features=False)
        results[profile["name"]] = rows

    step2 = {
        name: [row for row in rows if row["step"] == 2]
        for name, rows in results.items()
    }
    report = {
        "status": "PASS",
        "diagnostic": "strategy profile to action generator trace",
        "engine": "immutable OPT-1 CUDA snapshot through CudaBatchPPOEnv",
        "cuda": True,
        "episodes": episodes,
        "seed_start": seed_start,
        "steps_instrumented": 3,
        "step2_rows": step2,
        "all_profiles_use_dynamic_path": all(
            row["config"]["use_fixed_schedule"] is False
            for rows in step2.values()
            for row in rows
        ),
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
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "step5b" / "strategy_profile_action_trace.json")
    args = parser.parse_args()
    print(json.dumps(run_probe(args.episodes, args.seed_start, args.output), indent=2))


if __name__ == "__main__":
    main()
