"""Step 3H-5 multi-seed parity validation for PairedSimV2.

This is still a diagnostic gate. Real kaggle_environments remains the source of
truth; PairedSimV2 is not approved for PPO rollout training until multi-seed
parity and later performance/CUDA gates pass.
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

from apex_next.gpu_engine.step3h_parity_audit import (  # noqa: E402
    _first_divergence,
    _replay_in_paired_sim,
    _run_real_kaggle,
    _unsupported_action_summary,
)


DEFAULT_REPORT = PROJECT_ROOT / "reports" / "step3h" / "parity" / "STEP3H_MULTI_SEED_PARITY.json"


def run_multiseed_parity(
    seeds: list[int],
    steps: int = 720,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    started = time.perf_counter()
    seed_reports = []

    for seed in seeds:
        seed_started = time.perf_counter()
        error = None
        divergence = None
        unsupported = None
        real_steps = 0
        sim_steps = 0
        try:
            actions, real_snapshots = _run_real_kaggle(seed=seed, steps=steps)
            sim_snapshots = _replay_in_paired_sim(seed=seed, actions=actions)
            divergence = _first_divergence(real_snapshots, sim_snapshots)
            unsupported = _unsupported_action_summary(actions)
            real_steps = len(real_snapshots) - 1
            sim_steps = len(sim_snapshots) - 1
        except Exception as exc:  # pragma: no cover - diagnostic report path
            error = f"{type(exc).__name__}: {exc}"

        pass_seed = (
            error is None
            and divergence is None
            and unsupported is not None
            and unsupported["unsupported_or_ignored_entries"] == 0
            and real_steps == 719
            and sim_steps == 719
        )
        seed_report = {
            "seed": seed,
            "status": "PASS" if pass_seed else "FAIL",
            "real_steps_recorded": real_steps,
            "sim_steps_replayed": sim_steps,
            "first_divergence": divergence,
            "unsupported_or_ignored_entries": None
            if unsupported is None
            else unsupported["unsupported_or_ignored_entries"],
            "unsupported_or_ignored_commands": None
            if unsupported is None
            else unsupported["unsupported_or_ignored_commands"],
            "error": error,
            "elapsed_seconds": round(time.perf_counter() - seed_started, 6),
        }
        seed_reports.append(seed_report)
        print(
            f"seed={seed} status={seed_report['status']} "
            f"real={real_steps} sim={sim_steps} "
            f"divergence={divergence} unsupported={seed_report['unsupported_or_ignored_entries']}",
            flush=True,
        )

    pass_count = sum(1 for item in seed_reports if item["status"] == "PASS")
    failures = [item for item in seed_reports if item["status"] != "PASS"]
    report = {
        "status": "PASS" if pass_count == len(seed_reports) else "FAIL",
        "step": "STEP 3H-5 - Multi-seed PairedSimV2 parity",
        "scope": "diagnostic only; no PPO or CUDA promotion from this gate alone",
        "steps_requested": steps,
        "required_real_steps": 719,
        "required_sim_steps": 719,
        "seeds_tested": len(seed_reports),
        "seeds_passed": pass_count,
        "seeds_failed": len(failures),
        "pass_rate": 0.0 if not seed_reports else pass_count / len(seed_reports),
        "first_failure": failures[0] if failures else None,
        "seed_reports": seed_reports,
        "acceptance": {
            "all_first_divergence_null": all(item["first_divergence"] is None for item in seed_reports),
            "all_unsupported_zero": all(item["unsupported_or_ignored_entries"] == 0 for item in seed_reports),
            "all_real_steps_719": all(item["real_steps_recorded"] == 719 for item in seed_reports),
            "all_sim_steps_719": all(item["sim_steps_replayed"] == 719 for item in seed_reports),
            "all_exceptions_zero": all(item["error"] is None for item in seed_reports),
        },
        "recommendation": _recommendation(failures),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _recommendation(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return (
            "20-seed parity gate passed. Next recommended gate is a 100-seed deterministic parity run "
            "before CUDA conversion or Step 5B PPO acceleration."
        )
    first = failures[0]
    return (
        f"Do not advance to CUDA or PPO. First failing seed is {first['seed']} with divergence "
        f"{first['first_divergence']} and error {first['error']}; reproduce and harden that transition."
    )


def _parse_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds:
        return [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    return list(range(args.seed_start, args.seed_start + args.count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3H-5 multi-seed PairedSimV2 parity.")
    parser.add_argument("--seed-start", type=int, default=39000)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="")
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_multiseed_parity(_parse_seeds(args), steps=args.steps, report_path=args.report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
