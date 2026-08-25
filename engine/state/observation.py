"""Observation parsing and normalized state representation."""
from __future__ import annotations
from typing import Dict, Any, List, Optional

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "interval": 0, "max_yield": 6, "ongoing": False, "last_plant": 24},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "interval": 0, "max_yield": 4, "ongoing": False, "last_plant": 25},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "interval": 1, "max_yield": 4, "ongoing": True, "last_plant": 17},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "interval": 2, "max_yield": 4, "ongoing": True, "last_plant": 14},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "interval": 0, "max_yield": 6, "ongoing": False, "last_plant": 16},
}

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
SELLABLE = ("MILK", "WOOL", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "EGG", "FERTILIZER")

def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

class Observation:
    """Immutable view over Kaggle environment observation."""
    def __init__(self, raw_obs: Dict[str, Any], raw_config: Optional[Dict[str, Any]] = None):
        self.raw_obs = raw_obs
        self.raw_config = raw_config or {}
        
        self.player: int = int(safe_get(raw_obs, "player", 0) or 0)
        self.opp_player: int = 1 - self.player
        
        self.day: int = int(safe_get(raw_obs, "day", 0) or 0)
        self.hour: int = int(safe_get(raw_obs, "hour", 0) or 0)
        self.step: int = int(safe_get(raw_obs, "step", self.day * 24 + self.hour) or 0)
        self.total_steps: int = int(safe_get(self.raw_config, "episodeSteps", 720) or 720)
        self.remaining_steps: int = max(0, self.total_steps - self.step)
        self.remaining_days: float = self.remaining_steps / 24.0
        
        self.farms: List[Dict[str, Any]] = list(safe_get(raw_obs, "farms", []) or [])
        self.market: Dict[str, Any] = dict(safe_get(raw_obs, "market", {}) or {})
        self.town: Dict[str, Any] = dict(safe_get(raw_obs, "town", {}) or {})
        self.private: Dict[str, Any] = dict(safe_get(raw_obs, "private", {}) or {})
