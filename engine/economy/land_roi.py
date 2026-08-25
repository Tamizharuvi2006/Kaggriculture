"""Land expansion valuation with dynamic travel penalty modeling."""
from __future__ import annotations
from typing import Dict, Any, List

LAND_PRICES = [1000, 2000, 4000]
LAND_ORDER = ["NE", "SW", "SE"]

class LandROIValuator:
    """Evaluates Land expansion ROI based on marginal tile revenue minus transit overhead."""

    @staticmethod
    def evaluate_land_expansion(
        unlocked: List[str],
        day: int,
        money: float,
        safe_cash_buffer: float,
        projected_strawberry_profit_per_tile: float = 350.0,
    ) -> Dict[str, Any]:
        n_unlocked = len(unlocked)
        if n_unlocked >= 4:
            return {"should_buy": False, "reason": "ALL_QUADRANTS_UNLOCKED", "marginal_roi": 0.0}

        next_idx = n_unlocked - 1  # 0 for NE ($1000), 1 for SW ($2000), 2 for SE ($4000)
        cost = LAND_PRICES[next_idx]
        quadrant = LAND_ORDER[next_idx]

        if money - cost < safe_cash_buffer:
            return {
                "should_buy": False,
                "reason": f"INSUFFICIENT_CASH_BUFFER (needs ${cost + safe_cash_buffer:.0f}, has ${money:.0f})",
                "marginal_roi": 0.0
            }

        remaining_days = max(0.0, 30.0 - day)
        
        # Quadrant 4 (SE) Transit Latency Penalty:
        # SE tiles are avg distance 7.5 from shed (vs 3.5 for NW, 5.0 for NE/SW).
        # Workers spend 40% more steps walking, requiring 3-4 extra hands ($150-$200/day).
        if quadrant == "SE":
            transit_penalty_per_day = 120.0
            cost_threshold = 4000.0
            # Land #4 needs at least 14 days of compounding to recover $4000 + $120/day wages
            feasible_production_days = remaining_days - 2.0
            potential_revenue = 16 * (projected_strawberry_profit_per_tile * (feasible_production_days / 10.0))
            net_profit = potential_revenue - cost - (transit_penalty_per_day * feasible_production_days)
            marginal_roi = net_profit / cost
            
            should_buy = (marginal_roi > 0.35 and day <= 12 and money >= 6500.0)
            return {
                "should_buy": should_buy,
                "quadrant": quadrant,
                "cost": cost,
                "marginal_roi": round(marginal_roi, 3),
                "reason": "SE_QUADRANT_THRESHOLD_PASSED" if should_buy else "SE_TRANSIT_PENALTY_EXCEEDS_ROI"
            }

        elif quadrant == "SW":  # Land #3 ($2000)
            should_buy = (day <= 20 and money - cost >= safe_cash_buffer)
            return {
                "should_buy": should_buy,
                "quadrant": quadrant,
                "cost": cost,
                "marginal_roi": 1.45,
                "reason": "SW_EXPANSION_OPTIMAL" if should_buy else "SW_PAST_CUTOFF"
            }

        else:  # Land #2 (NE, $1000)
            should_buy = (day <= 22 and money - cost >= safe_cash_buffer)
            return {
                "should_buy": should_buy,
                "quadrant": quadrant,
                "cost": cost,
                "marginal_roi": 2.80,
                "reason": "NE_EXPANSION_OPTIMAL" if should_buy else "NE_PAST_CUTOFF"
            }
