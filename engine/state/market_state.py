"""Market state tracker with velocity, acceleration, and regime classification."""
from __future__ import annotations
from typing import Dict, List, Any, Optional
from engine.state.observation import Observation, PRODUCTS

# Exact Kaggriculture v1.32.7 Market Parameters
MARKET_I0 = 10000
PRICE_FLOOR = 1

MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": MARKET_I0, "T": 450, "below_func": "hinge",  "below_target": 1.00, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": MARKET_I0, "T": 200, "below_func": "hinge",  "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": MARKET_I0, "T": 332, "below_func": "hinge",  "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

class MarketTracker:
    """Stateful market history and telemetry tracker across simulation steps."""
    def __init__(self):
        self.price_history: Dict[str, List[float]] = {p: [] for p in PRODUCTS}
        self.inventory_history: Dict[str, List[float]] = {p: [] for p in PRODUCTS}
        self.last_step: int = -1

    def reset(self):
        self.price_history = {p: [] for p in PRODUCTS}
        self.inventory_history = {p: [] for p in PRODUCTS}
        self.last_step = -1

    def update(self, obs: Observation) -> MarketState:
        prices_raw = obs.market.get("prices", {}) or {}
        inv_raw = obs.market.get("inventory", {}) or {}
        
        step = obs.step
        if step == 0 or step <= self.last_step:
            self.reset()
        self.last_step = step

        current_prices = {}
        current_inv = {}
        for p in PRODUCTS:
            p_val = float(prices_raw.get(p, MARKET_PARAMS[p]["base"]))
            i_val = float(inv_raw.get(p, MARKET_I0))
            current_prices[p] = p_val
            current_inv[p] = i_val
            self.price_history[p].append(p_val)
            self.inventory_history[p].append(i_val)

        return MarketState(obs, current_prices, current_inv, self.price_history, self.inventory_history)

class MarketState:
    """Snapshot of market condition at a single turn."""
    def __init__(
        self,
        obs: Observation,
        prices: Dict[str, float],
        inventory: Dict[str, float],
        price_history: Dict[str, List[float]],
        inventory_history: Dict[str, List[float]],
    ):
        self.step: int = obs.step
        self.day: int = obs.day
        self.hour: int = obs.hour
        self.prices: Dict[str, float] = prices
        self.inventory: Dict[str, float] = inventory
        self.price_history: Dict[str, List[float]] = price_history
        self.inventory_history: Dict[str, List[float]] = inventory_history
        self.unlocked_shops: List[str] = list(obs.town.get("unlocked_shops", []) or [])

    def price(self, product: str) -> float:
        return self.prices.get(product, float(MARKET_PARAMS.get(product, {}).get("base", 25.0)))

    def velocity(self, product: str, window: int = 1) -> float:
        hist = self.price_history.get(product, [])
        if len(hist) <= window:
            return 0.0
        return hist[-1] - hist[-1 - window]

    def acceleration(self, product: str) -> float:
        hist = self.price_history.get(product, [])
        if len(hist) < 3:
            return 0.0
        v_now = hist[-1] - hist[-2]
        v_prev = hist[-2] - hist[-3]
        return v_now - v_prev

    def relative_price_ratio(self, product: str) -> float:
        base = float(MARKET_PARAMS.get(product, {}).get("base", 25.0))
        return self.price(product) / max(1.0, base)

    def town_drain_rate(self, product: str) -> float:
        """Returns units drained per turn by town shops + town center."""
        # Town center: 1 unit every 24 steps -> 1/24 per turn
        rate = 1.0 / 24.0
        for shop in self.unlocked_shops:
            prods = SHOPS.get(shop, [])
            if product in prods:
                mult = 2.0 if len(prods) == 1 else 1.0
                rate += mult / 4.0  # Shop sells every 4 steps
        return rate
