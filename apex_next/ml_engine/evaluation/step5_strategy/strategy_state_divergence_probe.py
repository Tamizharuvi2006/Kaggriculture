"""Locate the first observable state divergence between fixed strategy profiles."""

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
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import _configured_apex4_agent, _opponent_pool
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import STRATEGY_PROFILES


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_freeze(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_freeze(value), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _diff_paths(left: Any, right: Any, prefix: str = "", limit: int = 24) -> list[dict[str, Any]]:
    if len(_diff_paths.seen) >= limit:
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                _diff_paths.seen.append({"path": path, "left": left.get(key), "right": right.get(key)})
            else:
                _diff_paths(left[key], right[key], path, limit)
                if len(_diff_paths.seen) >= limit:
                    break
    elif left != right:
        _diff_paths.seen.append({"path": prefix, "left": left, "right": right})
    return _diff_paths.seen


def _first_diff(left: Any, right: Any) -> list[dict[str, Any]]:
    _diff_paths.seen = []
    return _diff_paths(_freeze(left), _freeze(right))


def run_probe(seed: int = 68000, output_path: Path | None = None) -> dict[str, Any]:
    opponent_pool = _opponent_pool()
    opponent_id, opponent_fn = opponent_pool[seed % len(opponent_pool)]
    traces: dict[str, list[dict[str, Any]]] = {}
    for profile_index, profile in enumerate(STRATEGY_PROFILES):
        env = CudaBatchPPOEnv([opponent_fn], device="cuda:0")
        env.reset([seed], extract_initial_features=False)
        agent = _configured_apex4_agent(profile["overrides"], module_suffix=932000 + profile_index)
        rows: list[dict[str, Any]] = []
        done = False
        while not done:
            public_before = env.observation(0, 0)
            before = {
                "public": public_before,
                "private": env.engine.private_observation(0, 0),
            }
            action = sanitize_action(call_agent(agent, public_before, env.configuration))
            _, _, done_list, infos = env.step([action], extract_next_features=False)
            after = {
                "public": env.observation(0, 0),
                "private": env.engine.private_observation(0, 0),
            }
            rows.append(
                {
                    "step": len(rows),
                    "action": action,
                    "state_digest": _digest(after),
                    "observation": after,
                    "opponent_action": infos[0].get("opponent_action"),
                }
            )
            done = bool(done_list[0])
        traces[profile["name"]] = rows

    baseline = "BALANCED"
    first_divergences: dict[str, dict[str, Any] | None] = {}
    for name, rows in traces.items():
        if name == baseline:
            continue
        first = None
        for left, right in zip(traces[baseline], rows):
            if left["state_digest"] != right["state_digest"]:
                first = {
                    "step": left["step"],
                    "state_field_diffs": _first_diff(left["observation"], right["observation"]),
                    "balanced_action": left["action"],
                    "strategy_action": right["action"],
                    "balanced_opponent_action": left["opponent_action"],
                    "strategy_opponent_action": right["opponent_action"],
                }
                break
        first_divergences[name] = first

    report = {
        "status": "PASS",
        "diagnostic": "fixed strategy state divergence probe",
        "seed": seed,
        "opponent_id": opponent_id,
        "cuda": True,
        "baseline": baseline,
        "strategies": list(traces),
        "steps_per_strategy": {name: len(rows) for name, rows in traces.items()},
        "first_state_divergences_vs_balanced": first_divergences,
        "sealed_production_modified": False,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=68000)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "step5b" / "strategy_state_divergence_probe.json")
    args = parser.parse_args()
    print(json.dumps(run_probe(args.seed, args.output), indent=2))


if __name__ == "__main__":
    main()
