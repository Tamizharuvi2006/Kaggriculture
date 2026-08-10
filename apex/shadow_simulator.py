"""L+ APEX 2.4: Shadow Simulation Engine & Execution Contract Verification.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
from apex.world_model import WorldState, CROPS, ANIMALS

class ShadowSimulationResult:
    def __init__(self, is_valid: bool, simulated_cash_after: float, risk_level: str, reason: str):
        self.is_valid = is_valid
        self.simulated_cash_after = simulated_cash_after
        self.risk_level = risk_level
        self.reason = reason

class ShadowSimulator:
    """Shadow Simulation Engine:
    Simulates counterfactual execution state without mutating real game state.
    Enforces Action Purity (0 appended market commands) and Liquidity Invariants.
    """

    @staticmethod
    def simulate_plan(plan_market_actions: List[List[Any]], state: WorldState) -> ShadowSimulationResult:
        current_cash = state.money
        operating_reserve = state.cash_state.operating_reserve

        projected_cost = 0.0
        projected_income = 0.0

        for ord in plan_market_actions:
            if not isinstance(ord, list) or len(ord) < 1:
                continue
            cmd = ord[0]
            if cmd == "SELL":
                item = ord[1] if len(ord) >= 2 else "WHEAT"
                qty = ord[2] if len(ord) >= 3 else 1
                price = float(state.prices.get(item, 10.0))
                projected_income += qty * price
            elif cmd == "BUY_SEED":
                crop = ord[1] if len(ord) >= 2 else "WHEAT"
                qty = ord[2] if len(ord) >= 3 else 1
                cost = CROPS.get(crop, {}).get("seed", 10.0) * qty
                projected_cost += cost
            elif cmd == "BUY_ANIMAL":
                animal = ord[1] if len(ord) >= 2 else "COW"
                cost = ANIMALS.get(animal, {}).get("cost", 400.0)
                projected_cost += cost
            elif cmd == "BUY_LAND":
                projected_cost += 500.0
            elif cmd == "HIRE":
                projected_cost += 100.0

        simulated_cash_after = current_cash + projected_income - projected_cost

        # 1. Hard Liquidity Invariant
        if simulated_cash_after < operating_reserve:
            return ShadowSimulationResult(
                is_valid=False,
                simulated_cash_after=simulated_cash_after,
                risk_level="CRITICAL_LIQUIDITY_PARALYSIS",
                reason=f"REJECTED_SIMULATED_CASH_${simulated_cash_after:.1f}_BELOW_RESERVE_${operating_reserve:.1f}"
            )

        # 2. Worker Maintenance Floor Invariant
        if simulated_cash_after <= 0.0:
            return ShadowSimulationResult(
                is_valid=False,
                simulated_cash_after=simulated_cash_after,
                risk_level="CATASTROPHIC_BANKRUPTCY",
                reason="REJECTED_SIMULATED_BANKRUPTCY"
            )

        return ShadowSimulationResult(
            is_valid=True,
            simulated_cash_after=simulated_cash_after,
            risk_level="LOW",
            reason="SHADOW_SIMULATION_SAFE"
        )
