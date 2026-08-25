"""Run a resumable controlled Step 5B PPO learning pilot in CUDA batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex_next.ml_engine.training.benchmark_strategy_selector_ppo import (
    DEFAULT_CLASSIFIER,
    run_step5b_batch_benchmark,
)


DEFAULT_INITIAL_SELECTOR = (
    PROJECT_ROOT / "apex_next" / "ml_engine" / "checkpoints" / "strategy_selector" / "strategy_selector_timing_smoke.pt"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "step5b" / "learning_pilot_500"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run_learning_pilot(
    episodes: int = 500,
    seed_start: int = 66000,
    decision_step: int = 120,
    initial_selector: Path = DEFAULT_INITIAL_SELECTOR,
    classifier: Path = DEFAULT_CLASSIFIER,
    output_dir: Path = DEFAULT_OUTPUT,
    batch_size: int = 32,
) -> dict:
    if episodes <= 0 or batch_size <= 0:
        raise ValueError("episodes and batch_size must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    batches: list[dict] = []
    current_selector = initial_selector
    completed = 0
    started = time.perf_counter()
    batch_index = 0

    while completed < episodes:
        count = min(batch_size, episodes - completed)
        report_path = output_dir / f"batch_{batch_index:02d}_{count}ep_report.json"
        checkpoint_path = output_dir / f"batch_{batch_index:02d}_{count}ep_selector.pt"
        result = run_step5b_batch_benchmark(
            episodes=count,
            seed_start=seed_start + completed,
            decision_step=decision_step,
            classifier_path=classifier,
            initial_selector_path=current_selector,
            checkpoint_path=checkpoint_path,
            report_path=report_path,
            require_cuda=True,
            batch_size=count,
        )
        if result["status"] != "PASS":
            raise RuntimeError(f"Pilot batch {batch_index} failed; see {report_path}")
        batches.append(
            {
                "batch_index": batch_index,
                "episodes": count,
                "seed_start": seed_start + completed,
                "report": str(report_path),
                "checkpoint": str(checkpoint_path),
                "mean_reward": result["reward_summary"]["mean"],
                "p05_reward": result["reward_summary"]["p05"],
                "win_rate": result["reward_summary"]["win_rate"],
                "rollout_games_per_second": result["timing"]["games_per_second_rollout"],
                "total_games_per_second": result["timing"]["games_per_second_total"],
                "ppo_update_seconds": result["timing"]["ppo_update_seconds"],
                "decision_step": result["decision_step"],
                "cuda": result["device"]["engine_tensor_device"] == "cuda:0",
            }
        )
        current_selector = checkpoint_path
        completed += count
        batch_index += 1

    elapsed = time.perf_counter() - started
    summary = {
        "status": "PASS" if completed == episodes else "FAIL",
        "step": "STEP 5B controlled PPO learning pilot",
        "episodes_requested": episodes,
        "episodes_completed": completed,
        "batch_size": batch_size,
        "batch_count": len(batches),
        "decision_step": decision_step,
        "seed_start": seed_start,
        "initial_selector": str(initial_selector),
        "initial_selector_sha256": _sha256(initial_selector),
        "classifier": str(classifier),
        "output_dir": str(output_dir),
        "elapsed_seconds": round(elapsed, 6),
        "batches": batches,
        "learning_curve": [
            {
                "batch_index": row["batch_index"],
                "episodes_completed": sum(item["episodes"] for item in batches[: row["batch_index"] + 1]),
                "mean_reward": row["mean_reward"],
                "p05_reward": row["p05_reward"],
                "win_rate": row["win_rate"],
            }
            for row in batches
        ],
        "long_training_started": False,
        "sealed_production_modified": False,
    }
    summary_path = output_dir / "pilot_500_summary.json"
    summary["summary_path"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled 500-episode Step 5B PPO pilot.")
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seed-start", type=int, default=66000)
    parser.add_argument("--decision-step", type=int, default=120)
    parser.add_argument("--initial-selector", type=Path, default=DEFAULT_INITIAL_SELECTOR)
    parser.add_argument("--classifier", type=Path, default=DEFAULT_CLASSIFIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(run_learning_pilot(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
