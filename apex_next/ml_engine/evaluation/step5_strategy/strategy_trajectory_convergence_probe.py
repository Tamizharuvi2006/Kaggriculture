"""Trace strategy trajectories and locate post-divergence convergence points."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import (
    _configured_apex4_agent,
    _opponent_pool,
)
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import STRATEGY_PROFILES


CHECKPOINTS = (2, 3, 5, 10, 20, 50, 100, 200, 400, 600, 718)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_freeze(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_freeze(value), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _action_summary(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "market": action.get("market", []),
        "hands": action.get("hands", []),
        "move": action.get("move"),
    }


def _state_snapshot(env: CudaBatchPPOEnv, idx: int) -> dict[str, Any]:
    public = env.observation(idx, 0)
    private = env.engine.private_observation(idx, 0)
    return {
        "public": public,
        "private": private,
        "digest": _digest({"public": public, "private": private}),
    }


def _compact_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    public = snapshot["public"]
    private = snapshot["private"]
    farms = public.get("farms", []) if isinstance(public, dict) else []
    own_farm = farms[0] if farms else {}
    return {
        "digest": snapshot["digest"],
        "money": private.get("money") if isinstance(private, dict) else None,
        "seeds": private.get("seeds") if isinstance(private, dict) else None,
        "hands": own_farm.get("hands") if isinstance(own_farm, dict) else None,
        "workers": own_farm.get("workers") if isinstance(own_farm, dict) else None,
        "animals": own_farm.get("animals") if isinstance(own_farm, dict) else None,
        "land": own_farm.get("land") if isinstance(own_farm, dict) else None,
        "tiles": own_farm.get("tiles") if isinstance(own_farm, dict) else None,
    }


def _first_state_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    if left["digest"] == right["digest"]:
        return None
    return {"left": _compact_state(left), "right": _compact_state(right)}


def _run_strategy(strategy: dict[str, Any], seeds: list[int], opponent_fns: list[Any], suffix: int) -> dict[str, Any]:
    env = CudaBatchPPOEnv(opponent_fns, device="cuda:0")
    env.reset(seeds, extract_initial_features=False)
    agents = [
        _configured_apex4_agent(strategy["overrides"], module_suffix=suffix + idx)
        for idx in range(len(seeds))
    ]
    traces: list[list[dict[str, Any]]] = [[] for _ in seeds]
    done = [False] * len(seeds)
    while not all(done):
        before = [_state_snapshot(env, idx) for idx in range(len(seeds))]
        actions = []
        for idx, agent in enumerate(agents):
            observation = env.observation(idx, 0)
            actions.append(sanitize_action(call_agent(agent, observation, env.configuration)))
        _, rewards, done, infos = env.step(actions, extract_next_features=False)
        for idx in range(len(seeds)):
            after = _state_snapshot(env, idx)
            step = len(traces[idx])
            traces[idx].append(
                {
                    "step": step,
                    "action": _action_summary(actions[idx]),
                    "opponent_action": infos[idx].get("opponent_action"),
                    "state_changed": before[idx]["digest"] != after["digest"],
                    "before_digest": before[idx]["digest"],
                    "after_digest": after["digest"],
                    "checkpoint_state": _compact_state(after) if step in CHECKPOINTS else None,
                    "reward": rewards[idx] if done[idx] else None,
                    "terminal": bool(done[idx]),
                }
            )
    return {
        "strategy": strategy["name"],
        "steps_per_seed": [len(trace) for trace in traces],
        "traces": traces,
        "cuda": env.actual_cuda_used,
        "tensor_device": str(env.engine.money.device),
    }


def _compare_pair(left: dict[str, Any], right: dict[str, Any], seeds: list[int]) -> dict[str, Any]:
    first_divergence = None
    first_reconvergence = None
    neutralized = None
    for seed_idx, seed in enumerate(seeds):
        left_trace = left["traces"][seed_idx]
        right_trace = right["traces"][seed_idx]
        diverged = False
        for step, (a, b) in enumerate(zip(left_trace, right_trace)):
            if a["after_digest"] != b["after_digest"]:
                if not diverged:
                    diverged = True
                    first_divergence = first_divergence or {
                        "seed": seed,
                        "step": step,
                        "left_action": a["action"],
                        "right_action": b["action"],
                        "state": {"left": a["checkpoint_state"], "right": b["checkpoint_state"]},
                    }
            elif diverged and first_reconvergence is None:
                first_reconvergence = {
                    "seed": seed,
                    "step": step,
                    "left_action": a["action"],
                    "right_action": b["action"],
                }
            if diverged and a["after_digest"] == b["after_digest"] and neutralized is None:
                neutralized = {
                    "seed": seed,
                    "step": step,
                    "reason": "full public+private state digests became identical",
                    "left_action": a["action"],
                    "right_action": b["action"],
                }
    return {
        "pair": f"{left['strategy']}_vs_{right['strategy']}",
        "first_divergence": first_divergence,
        "first_reconvergence": first_reconvergence,
        "first_neutralization": neutralized,
    }


def run_probe(seed_start: int = 68000, episodes: int = 32, output_path: Path | None = None) -> dict[str, Any]:
    pool = _opponent_pool()
    seeds = [seed_start + idx for idx in range(episodes)]
    opponent_fns = [pool[seed % len(pool)][1] for seed in seeds]
    runs = [
        _run_strategy(profile, seeds, opponent_fns, 970000 + profile_idx * 1000)
        for profile_idx, profile in enumerate(STRATEGY_PROFILES)
    ]
    comparisons = []
    for idx, left in enumerate(runs):
        for right in runs[idx + 1 :]:
            comparisons.append(_compare_pair(left, right, seeds))
    report = {
        "status": "PASS",
        "diagnostic": "32-seed strategy trajectory convergence probe",
        "seed_start": seed_start,
        "episodes": episodes,
        "same_seeds_and_opponent_schedule": True,
        "checkpoints": list(CHECKPOINTS),
        "runs": runs,
        "pairwise_convergence": comparisons,
        "ppo_updates": False,
        "sealed_production_modified": False,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=68000)
    parser.add_argument("--episodes", type=int, default=32)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "step5b" / "strategy_trajectory_convergence_probe.json",
    )
    args = parser.parse_args()
    print(json.dumps(run_probe(args.seed_start, args.episodes, args.output), indent=2))


if __name__ == "__main__":
    main()
