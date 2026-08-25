"""Step 3H-7 corrected vector-engine performance benchmark.

This benchmark separates:
- real Kaggriculture action-trace collection
- corrected vector replay core time

It does not use CUDA and does not treat the simulator as training truth beyond
the parity gates already produced by ``step3h7_vector_port_audit.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.gpu_engine.paired_gpu_v25.corrected_vector_engine import CorrectedVectorPairedEngine  # noqa: E402
from apex_next.gpu_engine.step3h_parity_audit import _resource_snapshot, _run_real_kaggle  # noqa: E402


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "vector" / "STEP3H7_VECTOR_PERFORMANCE.json"


def run_benchmark(seeds: list[int], steps: int = 719, report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    started = time.perf_counter()
    before = _resource_snapshot()

    collect_started = time.perf_counter()
    traces = []
    for seed in seeds:
        actions, _ = _run_real_kaggle(seed=seed, steps=steps)
        if len(actions) != steps:
            raise RuntimeError(f"Seed {seed} produced {len(actions)} actions, expected {steps}")
        traces.append(actions)
    collect_elapsed = time.perf_counter() - collect_started

    batch_started = time.perf_counter()
    actions_by_step = [
        (
            [trace[step_idx]["p0"] for trace in traces],
            [trace[step_idx]["p1"] for trace in traces],
        )
        for step_idx in range(steps)
    ]
    batch_elapsed = time.perf_counter() - batch_started

    engine = CorrectedVectorPairedEngine(batch_size=len(seeds), base_seed=seeds[0] if seeds else 0)
    engine.reset(seeds)
    core_started = time.perf_counter()
    for actions_p0, actions_p1 in actions_by_step:
        engine.step(actions_p0, actions_p1)
    core_elapsed = time.perf_counter() - core_started
    after = _resource_snapshot()

    total_transitions = len(seeds) * steps
    report = {
        "status": "PASS",
        "step": "STEP 3H-7I - Corrected vector performance benchmark",
        "backend": "CorrectedVectorPairedEngine",
        "actual_cuda_used": False,
        "uses_real_kaggle_truth_for_action_trace": True,
        "seeds_tested": len(seeds),
        "steps_per_seed": steps,
        "total_transitions_replayed": total_transitions,
        "timing_seconds": {
            "action_trace_collection_real_kaggle": round(collect_elapsed, 6),
            "action_batch_construction": round(batch_elapsed, 6),
            "corrected_vector_core_replay": round(core_elapsed, 6),
            "total_wall": round(time.perf_counter() - started, 6),
        },
        "throughput": {
            "core_games_per_sec": round(len(seeds) / core_elapsed, 4) if core_elapsed > 0 else None,
            "core_steps_per_sec": round(total_transitions / core_elapsed, 2) if core_elapsed > 0 else None,
            "including_collection_games_per_sec": round(len(seeds) / (time.perf_counter() - started), 4),
        },
        "resources": {"before": before, "after": after},
        "recommendation": "Use this as the corrected NumPy/vector baseline before considering CUDA conversion.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark corrected vector engine core replay.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=719)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_benchmark(_parse_seeds(args), steps=args.steps, report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
