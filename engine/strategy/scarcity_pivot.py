"""Dynamic Scarcity-Aware Opportunity Evaluator with explicit causal attribution."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from engine.state.observation import Observation
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketState
from engine.state.opponent_state import OpponentState
from engine.market.scarcity import ScarcityDetector, ScarcityReport
from engine.economy.crop_roi import CropROIValuator, CropEconomics
from engine.safety.solvency import SolvencyGuard
from engine.safety.feed_buffer import FeedBufferGuard

class ScarcityDecision:
    """Structured decision output with complete forensic trace."""
    def __init__(
        self,
        chosen_crop: str,
        expected_terminal_value: float,
        alternatives: Dict[str, float],
        scarcity_reports: Dict[str, ScarcityReport],
        crop_economics: Dict[str, CropEconomics],
        solvency_status: Dict[str, Any],
        decision_reason: str,
    ):
        self.chosen_crop = chosen_crop
        self.expected_terminal_value = expected_terminal_value
        self.alternatives = alternatives
        self.scarcity_reports = scarcity_reports
        self.crop_economics = crop_economics
        self.solvency_status = solvency_status
        self.decision_reason = decision_reason

    def to_formatted_trace(self, step: int) -> str:
        """Returns human-readable forensic log formatted exactly to user spec."""
        chosen_econ = self.crop_economics.get(self.chosen_crop)
        chosen_scarcity = self.scarcity_reports.get(self.chosen_crop)
        
        trace = [
            f"TURN {step}",
            f"Decision: ALLOCATE {self.chosen_crop}",
            f"Expected terminal net value: +${self.expected_terminal_value:.0f}",
        ]
        for alt_crop, val in sorted(self.alternatives.items(), key=lambda x: x[1], reverse=True):
            if alt_crop != self.chosen_crop:
                trace.append(f"Alternative: {alt_crop:<12} +${val:.0f}")
        
        if chosen_scarcity:
            trace.append("Market:")
            trace.append(f"  {self.chosen_crop.lower()} price: ${chosen_scarcity.price:.0f}")
            trace.append(f"  velocity: {chosen_scarcity.velocity:+.1f}/turn")
            trace.append(f"  knee status: {chosen_scarcity.knee_status}")
            trace.append(f"  scarcity index: {chosen_scarcity.scarcity_index:.2f}")
        
        if chosen_econ:
            trace.append("Costs:")
            trace.append(f"  seed: -${chosen_econ.seed_cost:.0f}")
            trace.append(f"  labor: -${chosen_econ.labor_cost:.1f}")
            trace.append(f"  travel: -${chosen_econ.travel_cost:.1f}")
            trace.append(f"  completion prob: {chosen_econ.completion_prob:.0%}")
            trace.append(f"  sale prob: {chosen_econ.sale_prob:.0%}")
        
        trace.append("Solvency:")
        trace.append(f"  cash remaining: ${self.solvency_status.get('cash_remaining', 0):.0f}")
        trace.append(f"  feed buffer: {self.solvency_status.get('feed_buffer_status', 'PASS')}")
        trace.append(f"  land constraint: {self.solvency_status.get('land_status', 'PASS')}")
        
        trace.append(f"Reason: {self.decision_reason}")
        return "\n".join(trace)

class ScarcityPivotEngine:
    """Evaluates candidate crop allocations and decides when to pivot from baseline."""

    @staticmethod
    def evaluate_planting_choice(
        obs: Observation,
        farm: FarmState,
        market: MarketState,
        opponent: OpponentState,
        candidate_slot_count: int = 4,
        distance_from_shed: float = 3.5,
    ) -> ScarcityDecision:
        candidate_crops = ["STRAWBERRY", "TOMATO", "CARROT", "MELON", "WHEAT"]
        
        scarcity_reports = {}
        economics = {}
        expected_net_values = {}

        for crop in candidate_crops:
            scarcity = ScarcityDetector.evaluate(crop, market, opponent)
            econ = CropROIValuator.evaluate_crop(
                crop, obs, market, opponent,
                planned_batch_qty=candidate_slot_count,
                distance_from_shed=distance_from_shed
            )
            scarcity_reports[crop] = scarcity
            economics[crop] = econ
            expected_net_values[crop] = econ.net_terminal_cash * candidate_slot_count

        # Incumbent baseline is STRAWBERRY (or MELON during early opening)
        incumbent = "MELON" if obs.day <= 2 else "STRAWBERRY"
        incumbent_value = expected_net_values[incumbent]

        # Candidate check: Choose crop with maximum expected net terminal cash
        best_crop = max(expected_net_values, key=lambda c: expected_net_values[c])
        best_value = expected_net_values[best_crop]

        # Solvency verification
        seed_cost = float(economics[best_crop].seed_cost * candidate_slot_count)
        cash_after = farm.money - seed_cost
        can_afford = SolvencyGuard.can_afford(farm.money, seed_cost, farm.unlocked_quadrants)
        feed_deficit = FeedBufferGuard.calculate_feed_deficit(farm, obs.day)

        solvency_status = {
            "cash_remaining": cash_after,
            "can_afford": can_afford,
            "feed_buffer_status": "DEFICIT" if feed_deficit > 0 else "PASS",
            "land_status": "PASS",
        }

        # Decision rule: Pivot ONLY if best crop is strictly superior to incumbent AND solvent
        if best_crop != incumbent and best_value > incumbent_value + 50.0 and can_afford:
            scarcity = scarcity_reports[best_crop]
            reason = f"{best_crop}_SCARCITY_UPSIDE_EXCEEDS_BASELINE (+$ {best_value - incumbent_value:.0f} delta, {scarcity.knee_status})"
            chosen_crop = best_crop
            chosen_val = best_value
        else:
            chosen_crop = incumbent
            chosen_val = incumbent_value
            reason = f"BASELINE_{incumbent}_OPTIMAL (no superior solvent alternative)"

        return ScarcityDecision(
            chosen_crop=chosen_crop,
            expected_terminal_value=chosen_val,
            alternatives=expected_net_values,
            scarcity_reports=scarcity_reports,
            crop_economics=economics,
            solvency_status=solvency_status,
            decision_reason=reason
        )
