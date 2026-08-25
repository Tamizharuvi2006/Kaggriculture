"""
APEX 4.0 World Model
Full closed-loop observation-driven state representation for Kaggriculture.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _get(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


class APEX4WorldModel:
    """
    Closed-loop state tracker updating on every live observation step.
    """
    def __init__(self):
        self.step = 0
        self.day = 0
        self.hour = 0
        self.player = 0
        
        # Farm State
        self.money = 0.0
        self.inventory = {}
        self.unlocked_quadrants = [0]
        self.tiles = []
        self.pastures = []
        self.workers = []
        self.farmer = {}
        
        # Market State
        self.market_prices = {}
        self.town_inventory = {}
        
        # Opponent Public State
        self.opp_money = 0.0
        self.opp_unlocked_quadrants = [0]
        self.opp_tiles = []
        self.opp_pastures = []

    def update(self, obs):
        self.step = int(_get(obs, "step", 0) or 0)
        self.day = self.step // 24
        self.hour = self.step % 24
        self.player = int(_get(obs, "player", 0) or 0)
        
        farms = _get(obs, "farms", []) or []
        if len(farms) > self.player:
            own_farm = farms[self.player]
            self.money = float(_get(own_farm, "money", 0.0) or 0.0)
            self.inventory = _get(own_farm, "inventory", {}) or {}
            self.unlocked_quadrants = _get(own_farm, "unlocked_quadrants", [0]) or [0]
            self.tiles = _get(own_farm, "tiles", []) or []
            self.pastures = _get(own_farm, "pastures", []) or []
            self.workers = _get(own_farm, "workers", []) or []
            self.farmer = _get(own_farm, "farmer", {}) or {}
            
        opp_player = 1 - self.player
        if len(farms) > opp_player:
            opp_farm = farms[opp_player]
            self.opp_money = float(_get(opp_farm, "money", 0.0) or 0.0)
            self.opp_unlocked_quadrants = _get(opp_farm, "unlocked_quadrants", [0]) or [0]
            self.opp_tiles = _get(opp_farm, "tiles", []) or []
            self.opp_pastures = _get(opp_farm, "pastures", []) or []
            
        market_obs = _get(obs, "market", {}) or {}
        self.market_prices = _get(market_obs, "prices", {}) or {}
        self.town_inventory = _get(market_obs, "inventory", {}) or {}

    def get_shed_item(self, item_name):
        return int(self.inventory.get(item_name, 0) or 0)

    def get_pasture_count(self):
        return len(self.pastures)

    def get_active_animals(self):
        cows = sum(len([a for a in _get(p, "animals", []) if _get(a, "type") == "COW"]) for p in self.pastures)
        sheep = sum(len([a for a in _get(p, "animals", []) if _get(a, "type") == "SHEEP"]) for p in self.pastures)
        return {"cows": cows, "sheep": sheep}
