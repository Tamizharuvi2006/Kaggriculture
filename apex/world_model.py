"""L+ APEX 2.5: World Model & Dynamic CashFlowState Representation (Fixed Step Calculation).
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 24},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False, "last_plant": 25},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True, "last_plant": 17},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True, "last_plant": 14},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False, "last_plant": 16},
}

ANIMALS = {
    "COW": {"cost": 400, "product": "MILK"},
    "SHEEP": {"cost": 500, "product": "WOOL"},
}

SELLABLE = ("MILK", "WOOL", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "EGG", "FERTILIZER")

class CashState:
    """Dynamic CashFlowState representing operating capacity and liquidity reserves."""
    def __init__(self, money: float, num_workers: int, day: int):
        self.current_cash = float(money)
        self.worker_maintenance = float(num_workers * 50.0)
        self.operating_reserve = 300.0 if day <= 20 else 150.0
        self.mandatory_cost = self.worker_maintenance + self.operating_reserve
        self.disposable_cash = max(0.0, self.current_cash - self.mandatory_cost)
        self.liquidity_risk = "HIGH" if self.current_cash < self.mandatory_cost else "LOW"

class WorldState:
    """Complete, self-contained world state model with CashState and accurate Tile Parsing."""
    def __init__(self, obs: Dict[str, Any]):
        self.day: int = int(obs.get("day", 0))
        self.hour: int = int(obs.get("hour", 0))
        # Accurately compute step from day and hour if step key is missing from observation
        self.step: int = int(obs.get("step", self.day * 24 + self.hour))
        self.total_steps: int = 720
        self.remaining_steps: int = max(0, self.total_steps - self.step)
        self.player_idx: int = int(obs.get("player", 0))
        self.opp_idx: int = 1 - self.player_idx

        # Market state
        market = obs.get("market", {}) or {}
        self.prices: Dict[str, float] = market.get("prices", {}) or {}

        # Player farm state
        farms = obs.get("farms", []) or []
        if len(farms) > self.player_idx:
            my_farm = farms[self.player_idx]
            self.money: float = float(my_farm.get("money", 0.0))
            self.unlocked_quadrants: List[str] = list(my_farm.get("unlocked_quadrants", []) or [])
            self.unlocked: List[str] = self.unlocked_quadrants
            self.inventory: Dict[str, int] = dict(my_farm.get("inventory", {}) or {})
            self.tiles: List[Dict[str, Any]] = [
                tile for row in (my_farm.get("tiles", []) or [])
                for tile in row if isinstance(tile, dict)
            ]
            self.workers: List[Dict[str, Any]] = list(my_farm.get("workers", []) or [])
            self.hires_today: int = int(my_farm.get("hires_today", 0))
        else:
            self.money = 0.0
            self.unlocked_quadrants = []
            self.inventory = {}
            self.tiles = []
            self.workers = []
            self.hires_today = 0

        # Opponent farm state
        if len(farms) > self.opp_idx:
            opp_farm = farms[self.opp_idx]
            self.opp_money: float = float(opp_farm.get("money", 0.0))
            self.opp_unlocked_quadrants: List[str] = list(opp_farm.get("unlocked_quadrants", []) or [])
            self.opp_unlocked: List[str] = self.opp_unlocked_quadrants
            self.opp_inventory: Dict[str, int] = dict(opp_farm.get("inventory", {}) or {})
            self.opp_tiles: List[Dict[str, Any]] = [
                tile for row in (opp_farm.get("tiles", []) or [])
                for tile in row if isinstance(tile, dict)
            ]
            self.opp_workers: List[Dict[str, Any]] = list(opp_farm.get("workers", []) or [])
        else:
            self.opp_money = 0.0
            self.opp_unlocked_quadrants = []
            self.opp_inventory = {}
            self.opp_tiles = []
            self.opp_workers = []

        # Dynamic CashFlowState & Tile Parsing Fix
        self.cash_state = CashState(self.money, len(self.workers), self.day)
        self.ready_harvests = [
            t for t in self.tiles
            if t.get("crop") is not None and t.get("yield", 0) > 0
        ]
