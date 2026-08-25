"""Labor valuation and hiring marginal return engine."""
from __future__ import annotations
from typing import Dict, Any

class LaborROIValuator:
    """Evaluates hiring costs against marginal task productivity."""

    @staticmethod
    def hire_cost(n_already_today: int, mult: int = 1) -> int:
        """Fibonacci hire cost scale."""
        a, b = 1, 1
        for _ in range(n_already_today):
            a, b = b, a + b
        return mult * a

    @staticmethod
    def should_hire_hand(
        hires_today: int,
        unserviced_tasks_count: int,
        current_money: float,
        safe_cash_buffer: float,
    ) -> bool:
        cost = LaborROIValuator.hire_cost(hires_today)
        if current_money - cost < safe_cash_buffer:
            return False
        # Each worker can complete ~20 actions per day
        needed_workers = (unserviced_tasks_count + 15) // 20
        return hires_today < needed_workers and cost <= 100
