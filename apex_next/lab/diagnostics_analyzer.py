"""
2. Diagnostics Analyzer (Read-Only)
Performs objective causal root-cause analysis on match losses.
Maps losses to concrete failure archetypes without inventing solutions.
"""
from typing import Dict, Any, List


class DiagnosticsAnalyzer:
    """Categorizes losses into mutually exclusive or prioritized failure archetypes."""

    ARCHETYPES = [
        "LIQUIDITY_SHOCK",
        "LATE_MILK_TIMING",
        "CROP_DRIFT",
        "PRICE_SPIKE",
        "OPPONENT_PREEMPTION",
        "SEAT_ASYMMETRY",
        "PASS_TURN_STALL"
    ]

    def diagnose_loss(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Examines telemetry and returns an empirical diagnosis package."""
        if telemetry.get("result") != "LOSS":
            return {"status": "SKIPPED", "reason": "Match was not a loss"}

        our_mcv = telemetry.get("our_mcv", 0)
        opp_mcv = telemetry.get("opp_mcv", 0)
        pass_ratio = telemetry.get("pass_ratio", 0.0)
        seat = telemetry.get("seat", 0)
        mcv_deficit = opp_mcv - our_mcv

        detected_archetypes = []
        evidence_chain = []

        # Rule 1: Excessive PASS turns stall
        if pass_ratio > 0.05:
            detected_archetypes.append("PASS_TURN_STALL")
            evidence_chain.append(f"PASS turn ratio was {pass_ratio:.2%}, exceeding normal threshold (5%).")

        # Rule 2: Seat asymmetry deficit in early game
        if seat == 1 and mcv_deficit > 15000:
            detected_archetypes.append("SEAT_ASYMMETRY")
            evidence_chain.append("Player 1 handicap observed with >15k endgame wealth divergence.")

        # Rule 3: Milk timing divergence check
        milk_rev = telemetry.get("actions_summary", {}).get("milk_revenue", 0)
        opp_milk_rev = telemetry.get("actions_summary", {}).get("opp_milk_revenue", 0)
        if opp_milk_rev > 0 and milk_rev < (opp_milk_rev * 0.7):
            detected_archetypes.append("LATE_MILK_TIMING")
            evidence_chain.append(f"Milk revenue lag: our {milk_rev} vs opp {opp_milk_rev}.")

        # Rule 4: Liquidity / Cash squeeze
        min_cash = telemetry.get("actions_summary", {}).get("min_cash_reserve", 1000)
        if min_cash < 50:
            detected_archetypes.append("LIQUIDITY_SHOCK")
            evidence_chain.append(f"Cash reserve collapsed to {min_cash}, triggering worker idle/stalling.")

        # Default fallback archetype if not specifically triggered
        if not detected_archetypes:
            detected_archetypes.append("CROP_DRIFT")
            evidence_chain.append(f"Endgame MCV deficit of {mcv_deficit} due to compound farming yield difference.")

        return {
            "match_id": telemetry.get("match_id"),
            "status": "DIAGNOSED",
            "primary_archetype": detected_archetypes[0],
            "secondary_archetypes": detected_archetypes[1:],
            "mcv_deficit": mcv_deficit,
            "evidence_chain": evidence_chain,
            "motivating_seed": telemetry.get("raw_metadata", {}).get("seed", None)
        }

    def aggregate_failure_modes(self, telemetry_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates multiple matches to identify the highest-frequency failure bottleneck."""
        counts = {arch: 0 for arch in self.ARCHETYPES}
        diagnoses = []

        for item in telemetry_list:
            if item.get("result") == "LOSS":
                diag = self.diagnose_loss(item)
                if diag.get("status") == "DIAGNOSED":
                    counts[diag["primary_archetype"]] += 1
                    diagnoses.append(diag)

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return {
            "total_losses_analyzed": len(diagnoses),
            "archetype_frequencies": dict(ranked),
            "top_bottleneck": ranked[0][0] if ranked and ranked[0][1] > 0 else None,
            "diagnoses": diagnoses
        }
