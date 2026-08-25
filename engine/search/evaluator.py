"""Fast lightweight state evaluator for Monte Carlo rollouts and Beam Search."""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import math

from engine.state.observation import Observation, CROPS, ANIMALS
from engine.state.farm_state import FarmState
from engine.state.market_state import MarketState

class StateEvaluator:
    """Computes fast heuristic and rollout terminal values for game states."""

    @staticmethod
    def evaluate_terminal_wealth(
        current_money: float,
        standing_strawberries: int,
        standing_cows: int,
        shed_inventory: Dict[str, int],
        market_prices: Dict[str, float],
        remaining_days: float,
        num_workers: int,
    ) -> float:
        """Projects terminal wealth at Turn 720 from current state summary."""
        # 1. Cash on hand
        total = current_money

        # 2. Shed inventory liquidation value
        for item, qty in shed_inventory.items():
            if qty > 0:
                p = market_prices.get(item, 100.0)
                total += qty * p

        # 3. Future strawberry harvest waves
        # Each standing strawberry yields 4 berries every 10 days
        strawberry_cycles = remaining_days / 10.0
        expected_berry_yield = standing_strawberries * 4.0 * strawberry_cycles
        p_straw = market_prices.get("STRAWBERRY", 120.0)
        total += expected_berry_yield * p_straw

        # 4. Future dairy milk waves
        # Each cow yields 1 milk every 2 days
        milk_cycles = remaining_days / 2.0
        expected_milk_yield = standing_cows * 1.0 * milk_cycles
        p_milk = market_prices.get("MILK", 160.0)
        total += expected_milk_yield * p_milk

        # 5. Future labor wage expenditures
        # Worker wages = Fibonacci index per worker per day
        daily_wages = (num_workers * (num_workers + 1)) / 2.0  # Approx wage sum
        total -= daily_wages * remaining_days

        # 6. Future cow feed expenditures (1 wheat per cow per day)
        p_wheat = market_prices.get("WHEAT", 25.0)
        total -= standing_cows * remaining_days * p_wheat

        return total
