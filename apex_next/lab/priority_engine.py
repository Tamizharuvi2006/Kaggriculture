"""
12. Experiment Priority Engine
Stops the research agent from chasing interesting-but-low-value ideas.
Scores every failure cluster by:

    Priority = Impact x Frequency x Confidence x Fixability

and forces the pipeline to pick exactly ONE archetype to attack next, based
on frozen evidence rather than novelty.
"""
from typing import Dict, Any, List, Optional


class PriorityEngine:
    def __init__(self, max_weight: float = 1.0):
        self.max_weight = max_weight

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    def score_archetype(
        self,
        archetype: str,
        frequency: float,
        impact: float,
        confidence: float = 0.5,
        fixability: float = 0.5
    ) -> Dict[str, Any]:
        """
        frequency : share of losses attributable to this archetype (0..1)
        impact    : severity of the archetype when it occurs (0..1)
        confidence: evidence quality for the diagnosis (0..1)
        fixability: how tractable a single-variable fix is (0..1)
        """
        f = self._clamp(frequency)
        i = self._clamp(impact)
        c = self._clamp(confidence)
        x = self._clamp(fixability)

        priority = i * f * c * x * 10.0

        return {
            "archetype": archetype,
            "frequency": round(f, 4),
            "impact": round(i, 4),
            "confidence": round(c, 4),
            "fixability": round(x, 4),
            "priority_score": round(priority, 2)
        }

    def rank_clusters(
        self,
        clusters: List[Dict[str, Any]],
        attempt_penalty: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Ranks failure clusters by priority. Optionally penalizes archetypes that
        have already been attempted many times (falsified) so the lab is forced
        to explore rather than re-attack saturated dead ends.

        clusters: [{"archetype": str, "frequency": float, "impact": float,
                    "confidence": float, "fixability": float}]
        """
        scored = []
        for cluster in clusters:
            entry = self.score_archetype(
                archetype=cluster["archetype"],
                frequency=cluster.get("frequency", 0.0),
                impact=cluster.get("impact", 0.0),
                confidence=cluster.get("confidence", 0.5),
                fixability=cluster.get("fixability", 0.5)
            )
            attempts = (attempt_penalty or {}).get(cluster["archetype"], 0)
            entry["prior_attempts"] = attempts
            entry["penalized_score"] = round(entry["priority_score"] * (0.75 ** attempts), 2)
            scored.append(entry)

        scored.sort(key=lambda x: x["penalized_score"], reverse=True)

        return {
            "ranking": scored,
            "selected_archetype": scored[0]["archetype"] if scored else None,
            "selected_priority": scored[0]["penalized_score"] if scored else 0.0,
            "total_clusters": len(scored)
        }

    def select_next_experiment(
        self,
        diagnostics_aggregate: Dict[str, Any],
        attempt_penalty: Optional[Dict[str, int]] = None,
        default_impact: float = 0.5,
        default_confidence: float = 0.5,
        default_fixability: float = 0.5
    ) -> Dict[str, Any]:
        """
        Convenience wrapper over DiagnosticsAnalyzer.aggregate_failure_modes()
        output. Converts the archetype frequency table into scored clusters and
        returns the single highest-priority hypothesis target.
        """
        frequencies = diagnostics_aggregate.get("archetype_frequencies", {})
        total = sum(frequencies.values())
        if total == 0:
            return {"selected_archetype": None, "ranking": [], "total_clusters": 0}

        clusters = [
            {
                "archetype": arch,
                "frequency": count / total,
                "impact": default_impact,
                "confidence": default_confidence,
                "fixability": default_fixability
            }
            for arch, count in frequencies.items()
            if count > 0
        ]
        return self.rank_clusters(clusters, attempt_penalty=attempt_penalty)


if __name__ == "__main__":
    engine = PriorityEngine()
    fake_failures = {
        "total_losses_analyzed": 25,
        "archetype_frequencies": {
            "LIQUIDITY_SHOCK": 8,
            "LATE_MILK_TIMING": 5,
            "CROP_DRIFT": 3,
            "PRICE_SPIKE": 9
        }
    }
    selection = engine.select_next_experiment(fake_failures, attempt_penalty={"LIQUIDITY_SHOCK": 3})
    print("Selected archetype:", selection["selected_archetype"])
    for rank in selection["ranking"]:
        print(f"  {rank['archetype']:<20} score={rank['penalized_score']}")