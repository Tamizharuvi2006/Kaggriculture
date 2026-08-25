"""Seat swap tournament runner with automatic multi-threaded/multi-core parallel execution."""
from __future__ import annotations
import os
import concurrent.futures
from typing import Dict, Any, List, Callable
from engine.evaluation.paired_replay import PairedEvaluator

class SeatSwapTournament:
    """Runs a battery of paired seed matches concurrently across all CPU cores."""

    @staticmethod
    def run_gauntlet(
        candidate_agent: Callable,
        control_agent: Callable,
        seeds: List[int],
        steps: int = 720,
        max_workers: int | None = None,
    ) -> Dict[str, Any]:
        if max_workers is None:
            max_workers = min(32, os.cpu_count() or 8)

        def _eval_seed(s: int) -> Dict[str, Any]:
            return PairedEvaluator.evaluate_pair(candidate_agent, control_agent, s, steps=steps)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for pair_res in executor.map(_eval_seed, seeds):
                results.append(pair_res)

        # Preserve original seed ordering
        results.sort(key=lambda x: seeds.index(x["seed"]))

        total_matches = len(seeds) * 2
        wins = sum(r["m1_win"] + r["m2_win"] for r in results)
        seat0_wins = sum(r["m1_win"] for r in results)
        seat1_wins = sum(r["m2_win"] for r in results)
        total_delta = sum(r["paired_delta"] for r in results)

        overall_win_rate = (wins / total_matches) if total_matches > 0 else 0.0
        mean_paired_delta = (total_delta / len(seeds)) if seeds else 0.0

        return {
            "num_seeds": len(seeds),
            "total_matches": total_matches,
            "overall_win_rate": round(overall_win_rate, 4),
            "seat0_win_rate": round(seat0_wins / len(seeds), 4) if seeds else 0.0,
            "seat1_win_rate": round(seat1_wins / len(seeds), 4) if seeds else 0.0,
            "mean_paired_delta": round(mean_paired_delta, 2),
            "total_delta": round(total_delta, 2),
            "detailed_results": results,
        }
