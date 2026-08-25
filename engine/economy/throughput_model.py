"""High-Fidelity Physical Throughput and Labor Capacity Model.
Accurately models the interaction between worker capacity, transit latency, watering deadlines, and harvest yield realization.
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import math

class PhysicalThroughputModel:
    """Models physical labor capacity vs farm workload to prevent compounding bottlenecks."""

    @staticmethod
    def calculate_workload(
        standing_strawberries: int,
        standing_cows: int,
        num_workers: int,
        transit_multiplier: float = 1.8,
    ) -> Dict[str, float]:
        """Calculates daily action demand vs worker supply."""
        # Supply: 24 steps per worker per day
        daily_capacity_steps = num_workers * 24.0

        # Demand:
        # 1. Watering: 1 action per strawberry per day
        water_steps = standing_strawberries * 1.0
        
        # 2. Harvesting: average 0.4 harvests per strawberry per day (4 berries every 10 days) + shed transit
        harvest_steps = standing_strawberries * 0.4 * 2.0  # Harvest + drop to shed
        
        # 3. Livestock: 1 feed + 0.5 milk per cow per day + pasture transit
        livestock_steps = standing_cows * 1.5 * 2.0

        total_demand_steps = (water_steps + harvest_steps + livestock_steps) * transit_multiplier

        labor_throughput_ratio = min(1.0, daily_capacity_steps / max(1.0, total_demand_steps))
        is_bottlenecked = (labor_throughput_ratio < 0.95)

        return {
            "daily_capacity_steps": daily_capacity_steps,
            "total_demand_steps": total_demand_steps,
            "labor_throughput_ratio": labor_throughput_ratio,
            "is_bottlenecked": is_bottlenecked,
        }

    @staticmethod
    def evaluate_terminal_wealth_with_throughput(
        current_money: float,
        standing_strawberries: int,
        standing_cows: int,
        shed_inventory: Dict[str, int],
        market_prices: Dict[str, float],
        remaining_days: float,
        num_workers: int,
    ) -> float:
        """Projects terminal wealth explicitly penalized by labor throughput bottlenecks."""
        throughput = PhysicalThroughputModel.calculate_workload(
            standing_strawberries, standing_cows, num_workers
        )
        throughput_ratio = throughput["labor_throughput_ratio"]

        # 1. Immediate Cash & Shed Liquidation
        total = current_money
        for item, qty in shed_inventory.items():
            if qty > 0:
                p = market_prices.get(item, 100.0)
                total += qty * p

        # 2. Future Strawberry Waves (Scaled by Throughput Realization!)
        p_straw = market_prices.get("STRAWBERRY", 120.0)
        strawberry_cycles = remaining_days / 10.0
        expected_berry_yield = standing_strawberries * 4.0 * strawberry_cycles * throughput_ratio
        total += expected_berry_yield * p_straw

        # 3. Future Dairy Waves (Scaled by Throughput Realization!)
        p_milk = market_prices.get("MILK", 160.0)
        milk_cycles = remaining_days / 2.0
        expected_milk_yield = standing_cows * 1.0 * milk_cycles * throughput_ratio
        total += expected_milk_yield * p_milk

        # 4. Labor Wages
        daily_wages = (num_workers * (num_workers + 1)) / 2.0
        total -= daily_wages * remaining_days

        # 5. Feed Costs
        p_wheat = market_prices.get("WHEAT", 25.0)
        total -= standing_cows * remaining_days * p_wheat

        return total
