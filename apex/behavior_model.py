"""L+ APEX 2.0: Behavioral Fingerprinting & Winning Pattern Model.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState

class BehaviorFingerprint:
    """Quantitative fingerprint of farm execution behavior."""
    def __init__(
        self,
        plant_rate: float,
        sell_rate: float,
        harvest_rate: float,
        hire_rate: float,
        crop_mix: Dict[str, float],
        market_latency: float,
        capital_efficiency: float,
        worker_utilization: float
    ):
        self.plant_rate = plant_rate
        self.sell_rate = sell_rate
        self.harvest_rate = harvest_rate
        self.hire_rate = hire_rate
        self.crop_mix = crop_mix
        self.market_latency = market_latency
        self.capital_efficiency = capital_efficiency
        self.worker_utilization = worker_utilization

    def similarity_to_winner_profile(self) -> float:
        """Returns similarity score (0.0 to 1.0) to empirically proven winner behavior.
        Empirical Winner Profile: Moderate planting (167), balanced harvesting (334), low sell latency.
        """
        # Winner profile targets
        target_harvest_rate = 0.46
        target_capital_eff = 0.85
        
        harvest_dist = abs(self.harvest_rate - target_harvest_rate)
        eff_dist = abs(self.capital_efficiency - target_capital_eff)
        
        score = max(0.0, 1.0 - (harvest_dist + eff_dist + self.market_latency * 0.5))
        return score

class BehaviorModel:
    """Extracts and evaluates behavioral fingerprints against winning replay patterns."""

    @staticmethod
    def extract_fingerprint(state: WorldState) -> BehaviorFingerprint:
        total_steps = max(1, state.step)
        
        plant_cnt = state.wheat_count + state.strawberries_count
        harvest_cnt = len(state.ready_harvests)
        total_workers = max(1, len(state.workers))

        crop_total = max(1, plant_cnt)
        crop_mix = {
            "STRAWBERRY": state.strawberries_count / crop_total,
            "WHEAT": state.wheat_count / crop_total,
        }

        # Market latency: high if inventory is sitting unsold
        inv_total = sum(state.inventory.values())
        market_latency = min(1.0, inv_total / 100.0)

        # Capital efficiency: money active in assets vs idle cash
        capital_eff = min(1.0, (state.money + inv_total * 20.0) / max(1.0, state.money + 500.0))

        return BehaviorFingerprint(
            plant_rate=plant_cnt / total_steps,
            sell_rate=inv_total / total_steps,
            harvest_rate=harvest_cnt / total_steps,
            hire_rate=state.hires_today / float(total_steps // 24 + 1),
            crop_mix=crop_mix,
            market_latency=market_latency,
            capital_efficiency=capital_eff,
            worker_utilization=min(1.0, harvest_cnt / total_workers)
        )
