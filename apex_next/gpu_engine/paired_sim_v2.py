"""
PAIRED_GPU_V2: In-Memory 2-Player Paired Simulation Engine
Simulates Candidate vs APEX 3.5 Baseline in a shared 2-player environment:
- Shared 10x10 farmland map with distinct quadrant ownership
- Shared Town Center & Town Shop market order book
- Step-by-step simultaneous action processing
- Paired seat-swapping harness (Seat 0 & Seat 1)
- 720-step deterministic horizon
"""
import copy
import math
import random
import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable


class PairedSimV2Engine:
    STEPS_PER_DAY = 24
    EPISODE_STEPS = 720
    TERMINAL_STEP = EPISODE_STEPS - 1
    PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
    CROPS = {
        "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
        "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
        "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
        "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
        "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
    }
    ANIMALS = {
        "GOOSE": {"cost": 300},
        "COW": {"cost": 400},
        "SHEEP": {"cost": 500},
    }
    LAND_ORDER = ["NE", "SW", "SE"]
    LAND_PRICES = [1000, 2000, 4000]
    TOWN_CENTER_PRODUCTS = [p for p in PRODUCTS if p != "FERTILIZER"]
    TOWN_SHOP_UNLOCK_INTERVAL = 3
    TOWN_SHOP_SELL_INTERVAL = 4
    MAX_SHOP_INSTANCES = 8
    SHOPS = {
        "BAKERY": ["EGG", "WHEAT"],
        "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
        "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
        "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
        "PET_CAFE": ["CARROT"],
        "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
        "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
        "YARN_STORE": ["WOOL"],
    }
    WEED_SPAWN_CHANCE = 0.005
    SHED_CAPACITY = 100
    
    BASE_PRICES = {
        "WHEAT": 25.0,
        "CARROT": 35.0,
        "TOMATO": 60.0,
        "STRAWBERRY": 120.0,
        "MELON": 250.0,
        "EGG": 50.0,
        "MILK": 160.0,
        "WOOL": 200.0,
        "FERTILIZER": 100.0
    }

    MARKET_I0 = 10000
    PRICE_FLOOR = 1
    MARKET_PARAMS = {
        "WHEAT": {"base": 25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt", "below_target": 0.80, "above_func": "log", "above_target": 0.20},
        "CARROT": {"base": 35, "I0": MARKET_I0, "T": 450, "below_func": "log", "below_target": 0.20, "above_func": "sqrt", "above_target": 0.70},
        "TOMATO": {"base": 60, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt", "above_target": 0.60},
        "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt", "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
        "MELON": {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.60},
        "EGG": {"base": 50, "I0": MARKET_I0, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log", "above_target": 0.20},
        "MILK": {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt", "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
        "WOOL": {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.20},
        "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0
        
        # Player states: 0 and 1
        self.money = np.array([3000.0, 3000.0], dtype=np.float64)
        self.land_count = np.array([1, 1], dtype=np.int32)
        self.shed_cows = np.array([0, 0], dtype=np.int32)
        self.shed_sheep = np.array([0, 0], dtype=np.int32)
        self.active_cows = np.array([0, 0], dtype=np.int32)
        self.active_sheep = np.array([0, 0], dtype=np.int32)
        self.pastures_count = np.array([0, 0], dtype=np.int32)
        self.cows = np.array([2, 2], dtype=np.int32)
        self.sheep = np.array([0, 0], dtype=np.int32)
        self.workers = np.array([0, 0], dtype=np.int32)
        self.hires_today = np.array([0, 0], dtype=np.int32)
        self.farmers = [[4, 4], [4, 4]]
        self.hands = [[], []]
        self.unlocked_quadrants = [["NW"], ["NW"]]
        self.tiles = [self._initial_tiles(), self._initial_tiles()]
        self.inventory = np.zeros((2, len(self.PRODUCTS)), dtype=np.float64)
        self.private_shed = [{item: 0 for item in self.PRODUCTS + list(self.ANIMALS)} for _ in range(2)]
        self.private_inventories = [[{}], [{}]]
        self.market_inventory = {product: self.MARKET_I0 for product in self.PRODUCTS}
        self.seeds = [{crop: 0 for crop in self.CROPS}, {crop: 0 for crop in self.CROPS}]
        self.private_animals = [{animal: 0 for animal in self.ANIMALS}, {animal: 0 for animal in self.ANIMALS}]
        self.town_shops = []
        
        # Market prices
        self.market_prices = np.array([self.BASE_PRICES[p] for p in self.PRODUCTS], dtype=np.float64)
        self.trajectory_log = []
        
    def reset(self, seed: Optional[int] = None) -> Dict[str, Any]:
        if seed is not None:
            self.seed = seed
            self.rng = np.random.RandomState(seed)
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0
        self.money[:] = 3000.0
        self.land_count[:] = 1
        self.shed_cows[:] = 0
        self.shed_sheep[:] = 0
        self.active_cows[:] = 0
        self.active_sheep[:] = 0
        self.pastures_count[:] = 0
        self.cows[:] = 2
        self.sheep[:] = 0
        self.workers[:] = 0
        self.hires_today[:] = 0
        self.farmers = [[4, 4], [4, 4]]
        self.hands = [[], []]
        self.unlocked_quadrants = [["NW"], ["NW"]]
        self.tiles = [self._initial_tiles(), self._initial_tiles()]
        self.inventory[:] = 0.0
        self.private_shed = [{item: 0 for item in self.PRODUCTS + list(self.ANIMALS)} for _ in range(2)]
        self.private_inventories = [[{}], [{}]]
        self.market_inventory = {product: self.MARKET_I0 for product in self.PRODUCTS}
        self.seeds = [{crop: 0 for crop in self.CROPS}, {crop: 0 for crop in self.CROPS}]
        self.private_animals = [{animal: 0 for animal in self.ANIMALS}, {animal: 0 for animal in self.ANIMALS}]
        self.town_shops = []
        self.market_prices[:] = [self.BASE_PRICES[p] for p in self.PRODUCTS]
        self.trajectory_log = []
        return self._get_obs(0), self._get_obs(1)
        
    def _get_obs(self, player_idx: int) -> Dict[str, Any]:
        opp_idx = 1 - player_idx
        obs = {
            "step": self.step_idx,
            "day": self.day_idx,
            "hour": self.hour_idx,
            "player": player_idx,
            "remainingOverageTime": 60.0,
            "farms": [
                {
                    "money": float(self.money[player_idx]),
                    "land": int(self.land_count[player_idx]),
                    "tiles": copy.deepcopy(self.tiles[player_idx]),
                    "farmer": list(self.farmers[player_idx]),
                    "hands": copy.deepcopy(self.hands[player_idx]),
                    "unlocked_quadrants": list(self.unlocked_quadrants[player_idx]),
                    "cows": int(self.cows[player_idx]),
                    "sheep": int(self.sheep[player_idx]),
                    "workers": int(self.workers[player_idx]),
                    "inventory": {self.PRODUCTS[i]: float(self.inventory[player_idx, i]) for i in range(len(self.PRODUCTS))}
                },
                {
                    "money": float(self.money[opp_idx]),
                    "land": int(self.land_count[opp_idx]),
                    "tiles": copy.deepcopy(self.tiles[opp_idx]),
                    "farmer": list(self.farmers[opp_idx]),
                    "hands": copy.deepcopy(self.hands[opp_idx]),
                    "unlocked_quadrants": list(self.unlocked_quadrants[opp_idx]),
                    "cows": int(self.cows[opp_idx]),
                    "sheep": int(self.sheep[opp_idx]),
                    "workers": int(self.workers[opp_idx]),
                    "inventory": {self.PRODUCTS[i]: float(self.inventory[opp_idx, i]) for i in range(len(self.PRODUCTS))}
                }
            ],
            "market": {
                "prices": {self.PRODUCTS[i]: float(self.market_prices[i]) for i in range(len(self.PRODUCTS))}
            }
        }
        return obs

    def _initial_tiles(self) -> List[List[Any]]:
        return [
            [None, None, None, None, None, "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            [None, None, None, None, None, "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            [None, None, None, None, None, "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            [None, None, None, None, None, "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            [None, None, None, None, None, "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            ["LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            ["LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            ["LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            ["LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
            ["LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED", "LOCKED"],
        ]

    def _shape(self, func: str, x: float) -> float:
        x = max(0.0, x)
        if func == "linear":
            return x
        if func == "sq":
            return x * x
        if func == "sqrt":
            return math.sqrt(x)
        if func == "log":
            return math.log(1.0 + x)
        if func == "log10":
            return math.log10(1.0 + x)
        return x

    def _market_price(self, item: str, inventory: float) -> float:
        params = self.MARKET_PARAMS[item]
        base = params["base"]
        i0 = params["I0"]
        t = params["T"]
        if inventory < i0:
            func = params["below_func"]
            amp = params["below_target"] * base / self._shape(func, t)
            price = base + amp * self._shape(func, i0 - inventory)
        else:
            func = params["above_func"]
            amp = params["above_target"] * base / self._shape(func, t)
            price = base - amp * self._shape(func, inventory - i0)
        return float(max(self.PRICE_FLOOR, int(round(price))))

    def _refresh_prices(self) -> None:
        for idx, product in enumerate(self.PRODUCTS):
            self.market_prices[idx] = self._market_price(product, self.market_inventory[product])

    def _hire_cost(self, hires_today: int) -> int:
        a, b = 1, 1
        for _ in range(hires_today):
            a, b = b, a + b
        return a

    def _spawn_hand(self, player_idx: int) -> List[int]:
        shed_tiles = [(4, 4), (5, 4), (4, 5), (5, 5)]
        occupants = {tile: 0 for tile in shed_tiles}
        for pos in [self.farmers[player_idx], *self.hands[player_idx]]:
            pos_tuple = tuple(pos)
            if pos_tuple in occupants:
                occupants[pos_tuple] += 1
        best = sorted(occupants.items(), key=lambda item: (item[1], shed_tiles.index(item[0])))
        return list(best[0][0])

    def _do_hire(self, player_idx: int) -> None:
        cost = self._hire_cost(int(self.hires_today[player_idx]))
        if self.money[player_idx] < cost:
            return
        self.money[player_idx] -= cost
        self.hires_today[player_idx] += 1
        self.hands[player_idx].append(self._spawn_hand(player_idx))
        self.private_inventories[player_idx].append({})
        self.workers[player_idx] = len(self.hands[player_idx])

    def _shed_used(self, player_idx: int) -> int:
        return int(sum(self.private_shed[player_idx].values()))

    def _deposit_to_shed(self, player_idx: int, item: str, qty: int) -> int:
        room = max(0, self.SHED_CAPACITY - self._shed_used(player_idx))
        take = min(max(0, int(qty)), room)
        if take > 0:
            self.private_shed[player_idx][item] = self.private_shed[player_idx].get(item, 0) + take
        return take

    def _do_buy_land(self, player_idx: int) -> None:
        unlocked_extra = len(self.unlocked_quadrants[player_idx]) - 1
        if unlocked_extra >= len(self.LAND_PRICES):
            return
        cost = self.LAND_PRICES[unlocked_extra]
        if self.money[player_idx] < cost:
            return
        self.money[player_idx] -= cost
        quadrant = self.LAND_ORDER[unlocked_extra]
        self.unlocked_quadrants[player_idx].append(quadrant)
        self.land_count[player_idx] = len(self.unlocked_quadrants[player_idx])
        for y in range(10):
            for x in range(10):
                tile_quadrant = ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
                if tile_quadrant == quadrant and self.tiles[player_idx][y][x] == "LOCKED":
                    self.tiles[player_idx][y][x] = None

    def _commit_market_unit(self, player_idx: int, op: str, item: str, price: float) -> bool:
        prod_idx = self.PRODUCTS.index(item) if item in self.PRODUCTS else -1
        if op == "SELL":
            if self.private_shed[player_idx].get(item, 0) <= 0:
                return False
            self.private_shed[player_idx][item] -= 1
            self.money[player_idx] += price
            if price > 1:
                self.market_inventory[item] += 1
            return True
        if op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
            if self.money[player_idx] < price or prod_idx < 0:
                return False
            if self._shed_used(player_idx) >= self.SHED_CAPACITY:
                return False
            self.money[player_idx] -= price
            self._deposit_to_shed(player_idx, item, 1)
            self.market_inventory[item] -= 1
            return True
        if op == "BUY_SEED" and item in self.CROPS:
            if self.money[player_idx] < price:
                return False
            self.money[player_idx] -= price
            self.seeds[player_idx][item] += 1
            return True
        if op == "BUY_ANIMAL" and item in self.ANIMALS:
            if self.money[player_idx] < price:
                return False
            if self._shed_used(player_idx) >= self.SHED_CAPACITY:
                return False
            self.money[player_idx] -= price
            self._deposit_to_shed(player_idx, item, 1)
            self.private_animals[player_idx][item] += 1
            return True
        return False

    def _parse_market_order(self, order: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(order, list) or not order:
            return None
        op = order[0]
        if op in ("HIRE", "BUY_LAND"):
            return {"type": op}
        if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL") and len(order) >= 3:
            try:
                remaining = int(order[2])
            except (TypeError, ValueError):
                return None
            if remaining <= 0:
                return None
            return {"type": op, "item": order[1], "remaining": remaining}
        return None

    def _process_market_orders(self, actions: List[Dict[str, Any]]) -> None:
        queues = []
        for action in actions:
            market_orders = action.get("market", []) if isinstance(action, dict) else []
            queues.append(list(market_orders)[:10] if isinstance(market_orders, list) else [])

        max_len = max((len(queue) for queue in queues), default=0)
        for order_idx in range(max_len):
            order_states = []
            for player_idx, queue in enumerate(queues):
                order_states.append(self._parse_market_order(queue[order_idx]) if order_idx < len(queue) else None)

            for player_idx, order_state in enumerate(order_states):
                if order_state is None:
                    continue
                if order_state["type"] == "HIRE":
                    self._do_hire(player_idx)
                    order_states[player_idx] = None
                elif order_state["type"] == "BUY_LAND":
                    self._do_buy_land(player_idx)
                    order_states[player_idx] = None

            while True:
                quoted = [None, None]
                for player_idx, order_state in enumerate(order_states):
                    if order_state is None or order_state.get("remaining", 0) <= 0:
                        continue
                    op = order_state["type"]
                    item = order_state["item"]
                    if op == "SELL" and item in self.PRODUCTS:
                        quoted[player_idx] = (op, item, self._market_price(item, self.market_inventory[item]), order_state)
                    elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                        quoted[player_idx] = (op, item, self._market_price(item, self.market_inventory[item] - 1), order_state)
                    elif op == "BUY_SEED" and item in self.CROPS:
                        quoted[player_idx] = (op, item, float(self.CROPS[item]["seed"]), order_state)
                    elif op == "BUY_ANIMAL" and item in self.ANIMALS:
                        quoted[player_idx] = (op, item, float(self.ANIMALS[item]["cost"]), order_state)
                    else:
                        order_states[player_idx] = None

                if all(item is None for item in quoted):
                    break

                committed_any = False
                for player_idx, quote in enumerate(quoted):
                    if quote is None:
                        continue
                    op, item, price, order_state = quote
                    if self._commit_market_unit(player_idx, op, item, price):
                        order_state["remaining"] -= 1
                        committed_any = True
                    else:
                        order_states[player_idx] = None
                if not committed_any:
                    break

            self._refresh_prices()

    def _town_consume(self) -> None:
        if self.step_idx % self.TOWN_SHOP_SELL_INTERVAL == 0:
            for shop_name in self.town_shops:
                products = self.SHOPS[shop_name]
                multiplier = 2 if len(products) == 1 else 1
                for product in products:
                    self.market_inventory[product] -= multiplier
        if self.step_idx % self.STEPS_PER_DAY == 0:
            for product in self.TOWN_CENTER_PRODUCTS:
                self.market_inventory[product] -= 1
        self._refresh_prices()

    def _unit_position(self, player_idx: int, unit_idx: int) -> Optional[List[int]]:
        if unit_idx == 0:
            return self.farmers[player_idx]
        hand_idx = unit_idx - 1
        if 0 <= hand_idx < len(self.hands[player_idx]):
            return self.hands[player_idx][hand_idx]
        return None

    def _set_unit_position(self, player_idx: int, unit_idx: int, pos: List[int]) -> None:
        if unit_idx == 0:
            self.farmers[player_idx] = pos
        else:
            self.hands[player_idx][unit_idx - 1] = pos

    def _unit_inventory(self, player_idx: int, unit_idx: int) -> Dict[str, int]:
        while len(self.private_inventories[player_idx]) <= unit_idx:
            self.private_inventories[player_idx].append({})
        return self.private_inventories[player_idx][unit_idx]

    def _is_shed_adjacent(self, pos: List[int]) -> bool:
        return tuple(pos) in {(4, 4), (5, 4), (4, 5), (5, 5)}

    def _take_inventory(self, inventory: Dict[str, int], item: str, qty: int = 1) -> bool:
        if inventory.get(item, 0) < qty:
            return False
        inventory[item] -= qty
        if inventory[item] == 0:
            del inventory[item]
        return True

    def _new_animal(self, item: str) -> Dict[str, Any]:
        structure = "PASTURE" if item in ("COW", "SHEEP") else "COOP"
        return {
            "kind": structure,
            "animal": item,
            "placed_day": self.day_idx,
            "yield_units": 0,
            "fed_today": False,
            "cared_today": False,
            "fertilizer_available": False,
            "consecutive_unfed": 0,
            "pending_care_bonus": 0,
        }

    def _new_plant(self, crop: str) -> Dict[str, Any]:
        crop_data = self.CROPS[crop]
        return {
            "kind": "PLANT",
            "crop": crop,
            "planted_day": self.day_idx,
            "watered_today": False,
            "consecutive_unwatered": 1,
            "yield_units": 0 if crop_data["ongoing"] else 1,
            "max_lifespan_step": -1 if crop_data["ongoing"] else (self.day_idx + crop_data["max_yield_day"] + 1) * self.STEPS_PER_DAY,
            "fertilized_until_day": -1,
        }

    def _apply_unit_action(self, player_idx: int, unit_idx: int, action: Any) -> None:
        if not isinstance(action, list) or not action:
            return
        pos = self._unit_position(player_idx, unit_idx)
        if pos is None:
            return
        op = action[0]
        moves = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
        if op in moves:
            dx, dy = moves[op]
            next_pos = [pos[0] + dx, pos[1] + dy]
            if 0 <= next_pos[0] < 10 and 0 <= next_pos[1] < 10:
                self._set_unit_position(player_idx, unit_idx, next_pos)
            return
        if op == "PASS":
            return

        fx, fy = pos
        tile = self.tiles[player_idx][fy][fx]
        inventory = self._unit_inventory(player_idx, unit_idx)

        if op == "DROP":
            if not self._is_shed_adjacent(pos):
                return
            for item, qty in list(inventory.items()):
                if qty > 0:
                    self._deposit_to_shed(player_idx, item, qty)
                del inventory[item]
            return

        if op == "PICKUP":
            if not self._is_shed_adjacent(pos) or len(action) < 2:
                return
            item = action[1]
            try:
                qty = int(action[2]) if len(action) >= 3 else 1
            except (TypeError, ValueError):
                return
            qty = min(max(0, qty), self.private_shed[player_idx].get(item, 0))
            if qty <= 0:
                return
            self.private_shed[player_idx][item] -= qty
            inventory[item] = inventory.get(item, 0) + qty
            return

        if op == "PLACE":
            if len(action) < 2:
                return
            item = action[1]
            if (
                item in self.ANIMALS
                and isinstance(tile, dict)
                and tile.get("kind") == ("PASTURE" if item in ("COW", "SHEEP") else "COOP")
                and "animal" not in tile
            ):
                if self._take_inventory(inventory, item, 1):
                    self.tiles[player_idx][fy][fx] = self._new_animal(item)
            elif self._is_shed_adjacent(pos):
                try:
                    qty = int(action[2]) if len(action) >= 3 else 1
                except (TypeError, ValueError):
                    return
                qty = min(max(0, qty), inventory.get(item, 0))
                deposited = self._deposit_to_shed(player_idx, item, qty)
                if deposited > 0:
                    inventory[item] -= deposited
                    if inventory[item] == 0:
                        del inventory[item]
            return

        if tile == "LOCKED":
            return
        if op == "PLANT":
            if len(action) < 2:
                return
            crop = action[1]
            if crop not in self.CROPS or tile is not None or self.seeds[player_idx].get(crop, 0) <= 0:
                return
            self.seeds[player_idx][crop] -= 1
            self.tiles[player_idx][fy][fx] = self._new_plant(crop)
            return
        if op == "WATER":
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
                tile["watered_today"] = True
                crop_data = self.CROPS[tile["crop"]]
                if not crop_data["ongoing"]:
                    age_days = self.day_idx - tile["planted_day"]
                    window_start = (crop_data["max_yield_day"] + 1) // 2
                    if window_start <= age_days <= crop_data["max_yield_day"]:
                        bonus = 2 if tile.get("fertilized_until_day", -1) >= self.day_idx else 1
                        tile["yield_units"] = min(crop_data["max_yield"], tile["yield_units"] + bonus)
            return
        if op == "HARVEST":
            if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
                return
            if tile.get("kind") == "PLANT":
                crop_data = self.CROPS[tile["crop"]]
                if self.day_idx - tile["planted_day"] < crop_data["first_yield_day"]:
                    return
                units = int(tile["yield_units"])
                tile["yield_units"] = 0
                inventory[tile["crop"]] = inventory.get(tile["crop"], 0) + units
                if not crop_data["ongoing"]:
                    self.tiles[player_idx][fy][fx] = None
            elif "animal" in tile:
                product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}[tile["animal"]]
                units = int(tile["yield_units"])
                tile["yield_units"] = 0
                inventory[product] = inventory.get(product, 0) + units
            return
        if op == "FERTILIZE":
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and self._take_inventory(inventory, "FERTILIZER", 1):
                tile["fertilized_until_day"] = max(tile.get("fertilized_until_day", -1), self.day_idx + 2)
            return
        if op == "DIG":
            if tile is not None and not (isinstance(tile, dict) and "animal" in tile):
                self.tiles[player_idx][fy][fx] = None
            return
        if op == "BUILD_PASTURE" and tile is None:
            self.tiles[player_idx][fy][fx] = {"kind": "PASTURE"}
            return
        if op == "BUILD_COOP" and tile is None:
            self.tiles[player_idx][fy][fx] = {"kind": "COOP"}
            return
        if op == "FEED":
            if isinstance(tile, dict) and "animal" in tile and not tile.get("fed_today", False):
                if self._take_inventory(inventory, "WHEAT", 1):
                    tile["fed_today"] = True
            return
        if op == "CARE":
            if isinstance(tile, dict) and "animal" in tile and not tile.get("cared_today", False):
                tile["cared_today"] = True
            return
        if op == "COLLECT_FERTILIZER":
            if isinstance(tile, dict) and "animal" in tile and tile.get("fertilizer_available", False):
                tile["fertilizer_available"] = False
                inventory["FERTILIZER"] = inventory.get("FERTILIZER", 0) + 1
            return

    def _daily_refresh_plants(self, player_idx: int) -> None:
        next_day = self.day_idx + 1
        for y, row in enumerate(self.tiles[player_idx]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                    continue
                was_watered = tile.get("watered_today", False)
                if was_watered:
                    tile["consecutive_unwatered"] = 0
                else:
                    tile["consecutive_unwatered"] = tile.get("consecutive_unwatered", 0) + 1
                tile["watered_today"] = False
                if tile["consecutive_unwatered"] >= 2:
                    self.tiles[player_idx][y][x] = {"kind": "WEED"}
                    continue
                crop_data = self.CROPS[tile["crop"]]
                if not crop_data["ongoing"]:
                    continue
                days_since_first = next_day - tile["planted_day"] - crop_data["first_yield_day"]
                if days_since_first < 0 or days_since_first % crop_data["interval"] != 0:
                    continue
                production_count = days_since_first // crop_data["interval"] + 1
                if production_count > crop_data["max_yield"]:
                    continue
                fertilized = was_watered and tile.get("fertilized_until_day", -1) >= self.day_idx
                tile["yield_units"] = min(crop_data["max_yield"], tile["yield_units"] + (2 if fertilized else 1))
                if production_count == crop_data["max_yield"]:
                    tile["max_lifespan_step"] = (next_day + 1) * self.STEPS_PER_DAY

    def _decay_plants(self, player_idx: int) -> None:
        for y, row in enumerate(self.tiles[player_idx]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                    continue
                max_lifespan_step = tile.get("max_lifespan_step", -1)
                if max_lifespan_step < 0 or self.step_idx < max_lifespan_step:
                    continue
                if (self.step_idx - max_lifespan_step) % 2 != 0:
                    continue
                tile["yield_units"] = tile.get("yield_units", 0) - 1
                if tile["yield_units"] <= 0:
                    self.tiles[player_idx][y][x] = {"kind": "WEED"}

    def _daily_refresh_animals(self, player_idx: int) -> None:
        next_day = self.day_idx + 1
        for y, row in enumerate(self.tiles[player_idx]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or "animal" not in tile:
                    continue
                if tile.get("fed_today", False):
                    tile["consecutive_unfed"] = 0
                else:
                    tile["consecutive_unfed"] = tile.get("consecutive_unfed", 0) + 1
                if tile["consecutive_unfed"] >= 2:
                    self.tiles[player_idx][y][x] = {"kind": "PASTURE" if tile["animal"] in ("COW", "SHEEP") else "COOP"}
                    continue
                animal_data = {
                    "GOOSE": {"first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
                    "COW": {"first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
                    "SHEEP": {"first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
                }[tile["animal"]]
                days_since_first = next_day - tile["placed_day"] - animal_data["first_yield_day"]
                if days_since_first >= 0 and days_since_first % animal_data["interval"] == 0:
                    bonus = tile.pop("pending_care_bonus", 0) if tile.get("fed_today", False) else 0
                    tile["yield_units"] = min(animal_data["max_held"], tile.get("yield_units", 0) + 1 + bonus)
                    tile["pending_care_bonus"] = 0
                if tile.get("cared_today", False) and tile.get("fed_today", False):
                    tile["pending_care_bonus"] = tile.get("pending_care_bonus", 0) + 1
                tile["fertilizer_available"] = True
                tile["fed_today"] = False
                tile["cared_today"] = False

    def _spawn_weeds(self, player_idx: int, rng: random.Random) -> None:
        for y, row in enumerate(self.tiles[player_idx]):
            for x, tile in enumerate(row):
                if tile is None and rng.random() < self.WEED_SPAWN_CHANCE:
                    self.tiles[player_idx][y][x] = {"kind": "WEED"}

    def _drop_inventories_to_shed(self, player_idx: int) -> None:
        shed = self.private_shed[player_idx]
        for inventory in self.private_inventories[player_idx]:
            for item, qty in list(inventory.items()):
                if qty > 0:
                    self._deposit_to_shed(player_idx, item, qty)
                del inventory[item]

    def _end_of_day(self) -> None:
        rng = random.Random((self.seed * 1_000_003) ^ self.day_idx)
        for player_idx in range(2):
            self._daily_refresh_plants(player_idx)
            self._daily_refresh_animals(player_idx)
            self._spawn_weeds(player_idx, rng)
            self._drop_inventories_to_shed(player_idx)
            self.farmers[player_idx] = [4, 4]
            self.hands[player_idx] = []
            self.workers[player_idx] = 0
            self.hires_today[player_idx] = 0
            self.private_inventories[player_idx] = [{}]
        next_day = self.day_idx + 1
        if next_day > 0 and next_day % self.TOWN_SHOP_UNLOCK_INTERVAL == 0 and len(self.town_shops) < self.MAX_SHOP_INSTANCES:
            self.town_shops.append(rng.choice(sorted(self.SHOPS)))
        
    def step(self, action_p0: Dict[str, Any], action_p1: Dict[str, Any]) -> Tuple[Tuple[Dict[str, Any], Dict[str, Any]], np.ndarray, bool, Dict[str, Any]]:
        # 1. Biological Production Cycles
        # Milk production every 6 hours from physically placed active cows
        if self.step_idx % 6 == 0 and self.step_idx > 0:
            self.inventory[0, 5] += self.active_cows[0] * 1.0  # MILK
            self.inventory[1, 5] += self.active_cows[1] * 1.0
            
        # Wool production every 72 hours (3 days) from physically placed active sheep
        if self.step_idx % 72 == 0 and self.step_idx > 0:
            self.inventory[0, 6] += self.active_sheep[0] * 2.0  # WOOL
            self.inventory[1, 6] += self.active_sheep[1] * 2.0
            
        # 2. Shared Market Order Book Execution
        actions = [action_p0, action_p1]
        for player_idx, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            self._apply_unit_action(player_idx, 0, action.get("farmer", ["PASS"]))
            hands_actions = action.get("hands", [])
            if isinstance(hands_actions, list):
                for hand_idx, hand_action in enumerate(hands_actions):
                    self._apply_unit_action(player_idx, hand_idx + 1, hand_action)
        self._process_market_orders(actions)
        self._town_consume()
        for player_idx in range(2):
            self._decay_plants(player_idx)

        if (self.step_idx + 1) % self.STEPS_PER_DAY == 0:
            self._end_of_day()
            
        self.step_idx += 1
        self.day_idx = self.step_idx // self.STEPS_PER_DAY
        self.hour_idx = self.step_idx % self.STEPS_PER_DAY
        
        done = self.step_idx >= self.TERMINAL_STEP
        obs_p0 = self._get_obs(0)
        obs_p1 = self._get_obs(1)
        rewards = self.money.copy()
        
        info = {
            "step": self.step_idx,
            "prices": self.market_prices.copy(),
            "p0_wealth": float(self.money[0]),
            "p1_wealth": float(self.money[1])
        }
        self.trajectory_log.append(info)
        return (obs_p0, obs_p1), rewards, done, info
        
    def run_paired_match(self, agent_cand: Callable, agent_base: Callable) -> Dict[str, Any]:
        """Runs match twice (Seat 0 vs Seat 1 and Seat 1 vs Seat 0) and merges results."""
        # Match A: Cand = Player 0, Base = Player 1
        obs_p0, obs_p1 = self.reset(self.seed)
        for step in range(self.EPISODE_STEPS):
            act0 = agent_cand(obs_p0)
            act1 = agent_base(obs_p1)
            (obs_p0, obs_p1), rew_a, done, _ = self.step(act0, act1)
            if done:
                break
        cand_mcv_a = rew_a[0]
        base_mcv_a = rew_a[1]
        
        # Match B: Base = Player 0, Cand = Player 1
        obs_p0, obs_p1 = self.reset(self.seed)
        for step in range(self.EPISODE_STEPS):
            act0 = agent_base(obs_p0)
            act1 = agent_cand(obs_p1)
            (obs_p0, obs_p1), rew_b, done, _ = self.step(act0, act1)
            if done:
                break
        base_mcv_b = rew_b[0]
        cand_mcv_b = rew_b[1]
        
        mean_cand_mcv = (cand_mcv_a + cand_mcv_b) / 2.0
        mean_base_mcv = (base_mcv_a + base_mcv_b) / 2.0
        delta_mcv = mean_cand_mcv - mean_base_mcv
        
        is_tie_a = abs(cand_mcv_a - base_mcv_a) < 1e-2
        is_tie_b = abs(cand_mcv_b - base_mcv_b) < 1e-2
        wins = (1.0 if cand_mcv_a > (base_mcv_a + 1e-2) else (0.5 if is_tie_a else 0.0)) + \
               (1.0 if cand_mcv_b > (base_mcv_b + 1e-2) else (0.5 if is_tie_b else 0.0))
        win_rate = wins / 2.0
        
        return {
            "seed": self.seed,
            "match_a": {"cand_mcv": cand_mcv_a, "base_mcv": base_mcv_a, "cand_seat": 0},
            "match_b": {"cand_mcv": cand_mcv_b, "base_mcv": base_mcv_b, "cand_seat": 1},
            "mean_cand_mcv": round(mean_cand_mcv, 2),
            "mean_base_mcv": round(mean_base_mcv, 2),
            "delta_mcv": round(delta_mcv, 2),
            "win_rate": win_rate
        }
