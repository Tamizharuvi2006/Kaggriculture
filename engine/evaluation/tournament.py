"""Multi-opponent tournament gauntlet across diverse opponent archetypes."""
from __future__ import annotations
import os
import sys
from typing import Dict, Any, List, Callable
from engine.evaluation.seat_swap import SeatSwapTournament

class TournamentEngine:
    """Runs a multi-opponent evaluation gauntlet."""

    @staticmethod
    def run_multi_opponent_gauntlet(
        candidate_agent: Callable,
        opponents: Dict[str, Callable],
        seeds: List[int],
        steps: int = 720,
    ) -> Dict[str, Any]:
        report = {}
        total_wins = 0.0
        total_matches = 0

        for opp_name, opp_agent in opponents.items():
            res = SeatSwapTournament.run_gauntlet(candidate_agent, opp_agent, seeds, steps=steps)
            report[opp_name] = res
            total_wins += res["overall_win_rate"] * res["total_matches"]
            total_matches += res["total_matches"]

        composite_win_rate = (total_wins / total_matches) if total_matches > 0 else 0.0

        return {
            "composite_win_rate": round(composite_win_rate, 4),
            "total_matches": total_matches,
            "opponents": report,
        }
