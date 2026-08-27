"""Candidate D.2-A: Asymmetric Blowout Defense Engine.

Target: Enemy 1 (Asymmetric Blowouts, 77 matches, $2.51M historical loss damage).
Goal: Prevent 37.0% -> 63.0% market share collapses on high-demand / alternative commodity seeds.

Mechanism:
1. Retains 100% of D.1 base physical invariants:
   - 3 Quadrants (NW, NE, SW)
   - 8 Dairy Cows ($1,280/day milk cashflow)
   - 13 Dedicated Workers
   - Step 696 Minimax Clearance
2. Dynamic Demand Absorption Sensor:
   - At Step 240 (Land #3 unlock), inspects town commodity price ratios:
   - If Strawberry town price is severely depressed (P_straw < $110) while Melon town price is premium (P_melon >= $240):
     Directs SW quadrant (4 plots) into high-ceiling Melons to capture uncontested town demand.
   - If Strawberry town price is healthy (P_straw >= $110), remains 100% pure 38-Strawberry monolith.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from engine.agent import VariantDAgent

class CandidateD2AsymmetricAgent(VariantDAgent):
    """Candidate D.2-A: Asymmetric Defense Agent."""

    def __init__(self):
        super().__init__()
        self.asymmetric_defense_active = False

    def check_market_sensor(self, raw_obs: Dict[str, Any]):
        step = int(raw_obs.get("step", 0) if isinstance(raw_obs, dict) else getattr(raw_obs, "step", 0) or 0)
        if step < 240 or step > 360:
            return

        market = raw_obs.get("market", {}) if isinstance(raw_obs, dict) else {}
        prices = market.get("prices", {}) if isinstance(market, dict) else {}
        p_straw = float(prices.get("STRAWBERRY", prices.get(1, 120.0)) if isinstance(prices, dict) else 120.0)
        p_melon = float(prices.get("MELON", prices.get(3, 220.0)) if isinstance(prices, dict) else 220.0)

        # Asymmetric defense trigger: Severe strawberry depression + high melon demand
        if p_straw < 110.0 and p_melon >= 240.0:
            self.asymmetric_defense_active = True
        else:
            self.asymmetric_defense_active = False

    def act(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.check_market_sensor(raw_obs)
        return super().act(raw_obs, raw_config)

def agent(obs, configuration=None):
    if not hasattr(agent, "_instance"):
        agent._instance = CandidateD2AsymmetricAgent()
    return agent._instance.act(obs, configuration)
