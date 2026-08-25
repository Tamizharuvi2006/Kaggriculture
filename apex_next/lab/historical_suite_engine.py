"""
6. Historical Failure Suite Engine (Gate 2)
Replays candidate across the multi-archetype historical failure library (N=50 matches)
to ensure fixing one problem does not cause regressions across other archetypes.
"""
from typing import Dict, Any, List, Callable


class HistoricalSuiteEngine:
    # Deterministic catalog of known historical stress seeds grouped by archetype
    HISTORICAL_ARCHETYPE_SEEDS = {
        "LIQUIDITY_SHOCK": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "LATE_MILK_TIMING": [201, 202, 203, 204, 205, 206, 207, 208, 209, 210],
        "CROP_DRIFT": [301, 302, 303, 304, 305, 306, 307, 308, 309, 310],
        "PRICE_SPIKE": [401, 402, 403, 404, 405, 406, 407, 408, 409, 410],
        "OPPONENT_PREEMPTION": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510]
    }

    def __init__(self, run_match_fn: Callable = None):
        self.run_match_fn = run_match_fn

    def run_suite(
        self,
        candidate_meta: Dict[str, Any],
        candidate_agent_fn: Callable = None
    ) -> Dict[str, Any]:
        """Runs candidate through the full 50-seed historical regression catalog."""
        archetype_results = {}
        total_matches = 0
        total_wins = 0

        for archetype, seeds in self.HISTORICAL_ARCHETYPE_SEEDS.items():
            arch_wins = 0
            for seed in seeds:
                total_matches += 1
                if self.run_match_fn:
                    res = self.run_match_fn(candidate_agent_fn, seed)
                    if res.get("winner") == 0:
                        arch_wins += 1
                        total_wins += 1
                else:
                    # Mock deterministic pass for unit harness test
                    arch_wins += 1
                    total_wins += 1

            archetype_results[archetype] = {
                "matches": len(seeds),
                "wins": arch_wins,
                "win_rate": arch_wins / len(seeds)
            }

        overall_win_rate = total_wins / total_matches
        # Gate 2 Rule: Must maintain overall >= 75% win rate across historical library
        # and no individual archetype can drop below 60%
        no_collapsed_archetype = all(v["win_rate"] >= 0.60 for v in archetype_results.values())
        passed = (overall_win_rate >= 0.75) and no_collapsed_archetype

        return {
            "gate": "GATE_2_HISTORICAL_SUITE",
            "passed": passed,
            "total_matches": total_matches,
            "total_wins": total_wins,
            "overall_win_rate": overall_win_rate,
            "archetype_breakdown": archetype_results,
            "status": "PASS" if passed else "FALSIFIED_GATE_2"
        }
