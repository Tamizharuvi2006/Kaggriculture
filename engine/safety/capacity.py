"""Shed capacity and overflow guardrails."""
from __future__ import annotations
from typing import Dict, Any
from engine.state.farm_state import FarmState

SHED_CAPACITY = 100

class CapacityGuard:
    """Manages shed capacity limits (100 units)."""

    @staticmethod
    def current_shed_usage(farm: FarmState) -> int:
        return sum(farm.shed.values())

    @staticmethod
    def remaining_shed_space(farm: FarmState) -> int:
        return max(0, SHED_CAPACITY - CapacityGuard.current_shed_usage(farm))

    @staticmethod
    def can_accept_deposit(farm: FarmState, quantity: int) -> bool:
        return CapacityGuard.remaining_shed_space(farm) >= quantity
