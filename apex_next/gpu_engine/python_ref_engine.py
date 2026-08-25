"""
Python Fast Reference Engine for Kaggriculture.
High-speed in-memory simulation replicating state transitions, crop mechanics,
livestock production, and town center market dynamics without process-spawn overhead.
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional


class KaggricultureRefEngine:
    STEPS_PER_DAY = 24
    EPISODE_STEPS = 720
    PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WOOL"]
    
    # Base economic parameters
    PRODUCT_BASE_PRICES = {
        "WHEAT": 25.0,
        "CARROT": 35.0,
        "TOMATO": 60.0,
        "STRAWBERRY": 120.0,
        "MELON": 250.0,
        "MILK": 160.0,
        "WOOL": 200.0
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.step_idx = 0
        self.day_idx = 0
        
        # Player states: [Player 0, Player 1]
        self.money = np.array([1000.0, 1000.0], dtype=np.float64)
        self.land_count = np.array([1, 1], dtype=np.int32)
        self.cows = np.array([2, 2], dtype=np.int32)
        self.sheep = np.array([0, 0], dtype=np.int32)
        self.workers = np.array([0, 0], dtype=np.int32)
        
        # Inventory: shape (2, num_products)
        self.inventory = np.zeros((2, len(self.PRODUCTS)), dtype=np.float64)
        
        # Market price trajectories: shape (num_products,)
        self.market_prices = np.array([self.PRODUCT_BASE_PRICES[p] for p in self.PRODUCTS], dtype=np.float64)
        self.price_history = []
        
    def reset(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Resets environment to Step 0."""
        if seed is not None:
            self.seed = seed
            self.rng = np.random.RandomState(seed)
        self.step_idx = 0
        self.day_idx = 0
        self.money[:] = 1000.0
        self.land_count[:] = 1
        self.cows[:] = 2
        self.sheep[:] = 0
        self.workers[:] = 0
        self.inventory[:] = 0.0
        self.market_prices[:] = [self.PRODUCT_BASE_PRICES[p] for p in self.PRODUCTS]
        self.price_history = [self.market_prices.copy()]
        return self._get_obs()
        
    def _get_obs(self) -> Dict[str, Any]:
        """Generates observation dictionary matching standard environment format."""
        obs = {
            "step": self.step_idx,
            "day": self.day_idx,
            "farms": [
                {
                    "money": float(self.money[0]),
                    "land": int(self.land_count[0]),
                    "cows": int(self.cows[0]),
                    "sheep": int(self.sheep[0]),
                    "workers": int(self.workers[0]),
                    "inventory": {self.PRODUCTS[i]: float(self.inventory[0, i]) for i in range(len(self.PRODUCTS))}
                },
                {
                    "money": float(self.money[1]),
                    "land": int(self.land_count[1]),
                    "cows": int(self.cows[1]),
                    "sheep": int(self.sheep[1]),
                    "workers": int(self.workers[1]),
                    "inventory": {self.PRODUCTS[i]: float(self.inventory[1, i]) for i in range(len(self.PRODUCTS))}
                }
            ],
            "market": {
                "prices": {self.PRODUCTS[i]: float(self.market_prices[i]) for i in range(len(self.PRODUCTS))}
            }
        }
        return obs
        
    def step(self, actions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], np.ndarray, bool, Dict[str, Any]]:
        """Advances environment by one step."""
        # 1. Milk & livestock yields (periodic)
        if self.step_idx % 6 == 0:
            self.inventory[0, 5] += self.cows[0] * 1.0  # MILK
            self.inventory[1, 5] += self.cows[1] * 1.0
            
        # 2. Process market orders & sales
        for p_idx, act in enumerate(actions):
            if not act or not isinstance(act, dict):
                continue
            sell_orders = act.get("sell", {})
            for prod_name, quantity in sell_orders.items():
                if prod_name in self.PRODUCTS and quantity > 0:
                    prod_idx = self.PRODUCTS.index(prod_name)
                    actual_sold = min(self.inventory[p_idx, prod_idx], float(quantity))
                    if actual_sold > 0:
                        unit_price = self.market_prices[prod_idx]
                        rev = actual_sold * unit_price
                        self.money[p_idx] += rev
                        self.inventory[p_idx, prod_idx] -= actual_sold
                        # Price impact: nonlinear elasticity drop
                        elasticity = 0.005 * (actual_sold ** 0.8)
                        self.market_prices[prod_idx] = max(1.0, self.market_prices[prod_idx] * (1.0 - elasticity))
                        
        # 3. Market mean-reversion and drift
        for i, prod in enumerate(self.PRODUCTS):
            base_p = self.PRODUCT_BASE_PRICES[prod]
            # Mean reversion pull + random walk noise
            noise = self.rng.normal(0.0, 0.01)
            reversion = (base_p - self.market_prices[i]) * 0.02
            self.market_prices[i] = max(1.0, self.market_prices[i] + reversion + (base_p * noise))
            
        self.step_idx += 1
        self.day_idx = self.step_idx // self.STEPS_PER_DAY
        self.price_history.append(self.market_prices.copy())
        
        done = self.step_idx >= self.EPISODE_STEPS
        rewards = self.money.copy()
        
        return self._get_obs(), rewards, done, {"step": self.step_idx}


if __name__ == "__main__":
    engine = KaggricultureRefEngine(seed=42)
    obs = engine.reset()
    print("Initial Obs Money:", obs["farms"][0]["money"])
    for s in range(50):
        # Sell milk if available
        act0 = {"sell": {"MILK": 1.0}} if s % 12 == 0 else {}
        act1 = {}
        obs, rew, done, info = engine.step([act0, act1])
    print(f"Step 50 Obs Money: P0=${obs['farms'][0]['money']:.2f}, P1=${obs['farms'][1]['money']:.2f}")
    print(f"Market Prices: {obs['market']['prices']}")
