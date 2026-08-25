"""Probe whether fixed strategy profiles produce distinct action traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.env_wrapper import call_agent, sanitize_action
from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import _configured_apex4_agent, _opponent_pool
from apex_next.ml_engine.training.cuda_batch_ppo_env import CudaBatchPPOEnv
from apex_next.ml_engine.training.train_strategy_selector_ppo import STRATEGY_PROFILES


def _canonical_hash(action: dict) -> str:
    payload = json.dumps(action, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_probe(seed: int = 68000, output_path: Path | None = None) -> dict:
    opponent_pool = _opponent_pool()
    opponent_id, opponent_fn = opponent_pool[seed % len(opponent_pool)]
    traces: dict[str, list[dict]] = {}
    for profile_index, profile in enumerate(STRATEGY_PROFILES):
        env = CudaBatchPPOEnv([opponent_fn], device="cuda:0")
        env.reset([seed], extract_initial_features=False)
        agent = _configured_apex4_agent(profile["overrides"], module_suffix=931000 + profile_index)
        rows: list[dict] = []
        done = False
        while not done:
            action = sanitize_action(call_agent(agent, env.observation(0, 0), env.configuration))
            rows.append({"step": len(rows), "hash": _canonical_hash(action), "action": action})
            _, _, done_list, _ = env.step([action], extract_next_features=False)
            done = bool(done_list[0])
        traces[profile["name"]] = rows

    names = list(traces)
    first_differences: dict[str, dict | None] = {}
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            key = f"{left}_vs_{right}"
            first = None
            for left_row, right_row in zip(traces[left], traces[right]):
                if left_row["hash"] != right_row["hash"]:
                    first = {
                        "step": left_row["step"],
                        "left_hash": left_row["hash"],
                        "right_hash": right_row["hash"],
                        "left_action": left_row["action"],
                        "right_action": right_row["action"],
                    }
                    break
            first_differences[key] = first

    report = {
        "status": "PASS",
        "diagnostic": "fixed strategy action trace probe",
        "seed": seed,
        "opponent_id": opponent_id,
        "cuda": True,
        "strategies": names,
        "steps_per_strategy": {name: len(rows) for name, rows in traces.items()},
        "first_differences": first_differences,
        "all_traces_identical": all(value is None for value in first_differences.values()),
        "traces": traces,
        "sealed_production_modified": False,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=68000)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "step5b" / "strategy_action_trace_probe.json")
    args = parser.parse_args()
    print(json.dumps(run_probe(args.seed, args.output), indent=2))


if __name__ == "__main__":
    main()
