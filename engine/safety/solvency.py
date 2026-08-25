"""Solvency and liquidity safety guardrails."""
from __future__ import annotations
from typing import List, Dict, Any
from engine.state.farm_state import FarmState

class SolvencyGuard:
    """Calculates mandatory operating reserves and enforces liquidity safety."""

    @staticmethod
    def get_safe_cash_buffer(unlocked: List[str]) -> float:
        """Dynamic liquidity buffer to guarantee critical milestone execution."""
        n_unlocked = len(unlocked)
        if n_unlocked == 1:
            return 1100.0  # Land #2 ($1000) + seed buffer ($100)
        elif n_unlocked == 2:
            return 2200.0  # Land #3 ($2000) + seed/wage buffer ($200)
        else:
            return 400.0   # Ongoing seed/wage/feed buffer

    @staticmethod
    def can_afford(current_money: float, cost: float, unlocked: List[str]) -> bool:
        buffer_req = SolvencyGuard.get_safe_cash_buffer(unlocked)
        return (current_money - cost) >= buffer_req

    @staticmethod
    def is_cash_constrained(farm: FarmState) -> bool:
        buffer_req = SolvencyGuard.get_safe_cash_buffer(farm.unlocked_quadrants)
        return farm.money < buffer_req
