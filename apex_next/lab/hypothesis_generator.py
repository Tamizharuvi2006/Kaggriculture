"""
3. Hypothesis Generator
Receives the diagnostic evidence package and generates an immutable, single-variable
hypothesis tied to a single variable family.
"""
import uuid
import datetime
from typing import Dict, Any, Optional


class HypothesisGenerator:
    """Enforces single-variable hypothesis formulation."""

    VARIABLE_FAMILIES = [
        "Pricing",
        "Inventory_Liquidity",
        "Timing",
        "Opponent_Adaptation",
        "Resource_Allocation"
    ]

    ARCHETYPE_TO_FAMILY = {
        "LIQUIDITY_SHOCK": "Inventory_Liquidity",
        "LATE_MILK_TIMING": "Timing",
        "CROP_DRIFT": "Resource_Allocation",
        "PRICE_SPIKE": "Pricing",
        "OPPONENT_PREEMPTION": "Opponent_Adaptation",
        "SEAT_ASYMMETRY": "Resource_Allocation",
        "PASS_TURN_STALL": "Timing"
    }

    def generate_hypothesis(
        self,
        diagnostic_package: Dict[str, Any],
        proposed_mechanism: str,
        variable_family: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates an immutable hypothesis specification."""
        archetype = diagnostic_package.get("primary_archetype", "CROP_DRIFT")
        family = variable_family or self.ARCHETYPE_TO_FAMILY.get(archetype, "Resource_Allocation")

        if family not in self.VARIABLE_FAMILIES:
            raise ValueError(f"Variable family '{family}' is not one of {self.VARIABLE_FAMILIES}")

        exp_num = int(datetime.datetime.utcnow().strftime("%m%d%H%M"))
        exp_id = f"EXP-{exp_num}"

        hypothesis_spec = {
            "experiment_id": exp_id,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "target_archetype": archetype,
            "variable_family": family,
            "motivating_match_id": diagnostic_package.get("match_id"),
            "motivating_seed": diagnostic_package.get("motivating_seed"),
            "evidence_summary": diagnostic_package.get("evidence_chain", []),
            "mechanism_hypothesis": proposed_mechanism.strip(),
            "expected_impact": f"Eliminate {archetype} failures without worsening baseline MCV tail distribution.",
            "status": "FORMULATED"
        }
        return hypothesis_spec
