"""Collect missing real Kaggriculture action traces without replay validation.

This is a resumable evidence-collection utility for Step 3H. It invokes the
real Kaggriculture environment once per missing seed and writes the same trace
schema used by the CUDA parity harness. Simulator replay is intentionally left
to the later cached parity gates.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.step3h8j_full_cuda_trajectory_audit import (  # noqa: E402
    DEFAULT_TRACE_DIR,
)
from apex_next.gpu_engine.step3h_parity_audit import (  # noqa: E402
    _run_real_kaggle,
    _unsupported_action_summary,
)


def _trace_path(trace_dir: Path, seed: int, steps: int) -> Path:
    return trace_dir / f"real_action_trace_seed_{seed}_steps_{steps}.json"


def _collect_one(seed: int, steps: int, trace_dir_text: str) -> dict[str, Any]:
    trace_dir = Path(trace_dir_text)
    path = _trace_path(trace_dir, seed, steps)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "seed": seed,
            "status": "CACHED",
            "path": str(path),
            "real_steps_recorded": payload.get("real_steps_recorded"),
            "action_count": len(payload.get("actions", [])),
        }

    started = time.perf_counter()
    actions, _snapshots = _run_real_kaggle(seed=seed, steps=steps)
    unsupported = _unsupported_action_summary(actions)
    real_steps = len(actions)
    payload = {
        "schema": "STEP3H_REAL_ACTION_TRACE_V1",
        "seed": seed,
        "steps_requested": steps,
        "real_steps_recorded": real_steps,
        "paired_steps_replayed": None,
        "real_vs_paired_reference_divergence": None,
        "unsupported_actions": unsupported,
        "collection_only": True,
        "actions": actions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "seed": seed,
        "status": "CREATED",
        "path": str(path),
        "real_steps_recorded": real_steps,
        "action_count": len(actions),
        "unsupported_or_ignored_entries": unsupported["unsupported_or_ignored_entries"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def collect_missing(
    seed_start: int,
    count: int,
    steps: int,
    workers: int,
    trace_dir: Path,
    report_path: Path,
) -> dict[str, Any]:
    seeds = list(range(seed_start, seed_start + count))
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_collect_one, seed, steps, str(trace_dir)): seed
            for seed in seeds
        }
        for future in as_completed(futures):
            results.append(future.result())
            results.sort(key=lambda item: item["seed"])
            print(json.dumps(results[-1], sort_keys=True), flush=True)

    created = [item for item in results if item["status"] == "CREATED"]
    invalid = [
        item
        for item in results
        if item.get("real_steps_recorded") != 719
        or item.get("action_count") != 719
        or item.get("unsupported_or_ignored_entries", 0) != 0
    ]
    report = {
        "status": "PASS" if len(results) == count and not invalid else "FAIL",
        "step": "STEP 3H - Missing real action trace collection",
        "collection_only": True,
        "seed_start": seed_start,
        "count_requested": count,
        "seeds_requested": seeds,
        "workers": workers,
        "trace_dir": str(trace_dir),
        "created_count": len(created),
        "cached_count": count - len(created),
        "invalid_count": len(invalid),
        "invalid_results": invalid,
        "results": results,
        "acceptance": {
            "all_requested_seeds_accounted_for": len(results) == count,
            "all_traces_have_719_actions": not invalid,
            "all_traces_have_zero_unsupported_actions": not invalid,
            "no_simulator_replay_during_collection": True,
        },
        "timing_seconds": {"total_wall": round(time.perf_counter() - started, 6)},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = collect_missing(
        seed_start=args.seed_start,
        count=args.count,
        steps=args.steps,
        workers=args.workers,
        trace_dir=args.trace_dir,
        report_path=args.report,
    )
    print(json.dumps({"status": report["status"], "created_count": report["created_count"], "invalid_count": report["invalid_count"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
