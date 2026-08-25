"""Parity-correct vector-engine port scaffold for Step 3H-7.

The older ``VectorizedPairedEngineV25`` is intentionally left intact as a speed
reference. This module starts the corrected V25-style batch port from the
validated ``PairedSimV2`` semantics, beginning with initial-state parity.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CorrectedVectorConfig:
    batch_size: int = 1
    episode_steps: int = 720
    terminal_step: int = 719
    board_size: int = 10
    shed_capacity: int = 100


class CorrectedVectorPairedEngine:
    """Batch state container for the parity-correct V25 port.

    Step 3H-7A only requires exact reset/initial observation parity. Transition
    mechanics are deliberately not implemented here yet; later 3H-7 gates should
    port market, action, movement, animal, crop, and terminal behavior in order.
    """

    PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
    CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
    ANIMALS = ["GOOSE", "COW", "SHEEP"]
    PRODUCT_INDEX = {product: idx for idx, product in enumerate(PRODUCTS)}
    STEPS_PER_DAY = 24
    WEED_SPAWN_CHANCE = 0.005
    BASE_PRICES = np.array([25.0, 35.0, 60.0, 120.0, 250.0, 50.0, 160.0, 200.0, 100.0], dtype=np.float32)
    MARKET_I0 = 10000
    PRICE_FLOOR = 1
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
    ANIMAL_COSTS = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
    CROP_DATA = {
        "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
        "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
        "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
        "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
        "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
    }
    CROP_SEED_COSTS = {crop: data["seed"] for crop, data in CROP_DATA.items()}

    def __init__(self, batch_size: int = 1, base_seed: int = 39000) -> None:
        self.config = CorrectedVectorConfig(batch_size=batch_size)
        self.N = int(batch_size)
        self.base_seed = int(base_seed)
        self.reset(list(range(self.base_seed, self.base_seed + self.N)))

    def reset(self, seeds: list[int] | None = None) -> None:
        if seeds is None:
            seeds = list(range(self.base_seed, self.base_seed + self.N))
        self.N = len(seeds)
        self.seeds = np.array(seeds, dtype=np.int64)
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0

        self.money = np.full((self.N, 2), 3000.0, dtype=np.float64)
        self.land_count = np.ones((self.N, 2), dtype=np.int32)
        self.workers = np.zeros((self.N, 2), dtype=np.int32)
        self.hires_today = np.zeros((self.N, 2), dtype=np.int32)
        self.active_cows = np.zeros((self.N, 2), dtype=np.int32)
        self.active_sheep = np.zeros((self.N, 2), dtype=np.int32)
        self.plant_tiles = np.zeros((self.N, 2), dtype=np.int32)
        self.animal_tiles = np.zeros((self.N, 2), dtype=np.int32)
        self.farmers = np.full((self.N, 2, 2), [4, 4], dtype=np.int32)
        self.hands: list[list[list[list[int]]]] = [[[], []] for _ in range(self.N)]
        self.unlocked_quadrants: list[list[list[str]]] = [[["NW"], ["NW"]] for _ in range(self.N)]
        self.tiles = [[self._initial_tiles(), self._initial_tiles()] for _ in range(self.N)]

        self.public_inventory = np.zeros((self.N, 2, len(self.PRODUCTS)), dtype=np.float64)
        self.private_shed = [
            [{item: 0 for item in self.PRODUCTS + self.ANIMALS} for _ in range(2)]
            for _ in range(self.N)
        ]
        self.private_inventories: list[list[list[dict[str, int]]]] = [[[{}], [{}]] for _ in range(self.N)]
        self.seeds_private = [
            [{crop: 0 for crop in self.CROPS} for _ in range(2)]
            for _ in range(self.N)
        ]

        self.market_inventory = np.full((self.N, len(self.PRODUCTS)), self.MARKET_I0, dtype=np.int32)
        self.market_prices = np.tile(self.BASE_PRICES, (self.N, 1)).astype(np.float64)
        self.town_shops: list[list[str]] = [[] for _ in range(self.N)]
        self._price_cache: list[dict[int, float]] = [dict() for _ in self.PRODUCTS]

    def _initial_tiles(self) -> list[list[Any]]:
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

    def observation(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        opp_idx = 1 - player_idx
        return {
            "step": self.step_idx,
            "day": self.day_idx,
            "hour": self.hour_idx,
            "player": player_idx,
            "farms": [
                self._farm(env_idx, player_idx),
                self._farm(env_idx, opp_idx),
            ],
            "market": {
                "inventory": {
                    product: int(self.market_inventory[env_idx, idx])
                    for idx, product in enumerate(self.PRODUCTS)
                },
                "prices": {
                    product: float(self.market_prices[env_idx, idx])
                    for idx, product in enumerate(self.PRODUCTS)
                },
            },
            "town": {"unlocked_shops": list(self.town_shops[env_idx])},
        }

    def _farm(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        return {
            "money": float(self.money[env_idx, player_idx]),
            "land": int(self.land_count[env_idx, player_idx]),
            "tiles": copy.deepcopy(self.tiles[env_idx][player_idx]),
            "farmer": self.farmers[env_idx, player_idx].astype(int).tolist(),
            "hands": copy.deepcopy(self.hands[env_idx][player_idx]),
            "unlocked_quadrants": list(self.unlocked_quadrants[env_idx][player_idx]),
            "inventory": {
                product: float(self.public_inventory[env_idx, player_idx, idx])
                for idx, product in enumerate(self.PRODUCTS)
            },
        }

    def private_observation(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        return {
            "shed": copy.deepcopy(self.private_shed[env_idx][player_idx]),
            "inventories": copy.deepcopy(self.private_inventories[env_idx][player_idx]),
            "seeds": copy.deepcopy(self.seeds_private[env_idx][player_idx]),
        }

    def step_market_only(self, actions_p0: list[dict[str, Any]], actions_p1: list[dict[str, Any]]) -> None:
        """Ported 3H-7B market transition.

        Physical action interpretation is intentionally excluded from this gate.
        """

        if len(actions_p0) != self.N or len(actions_p1) != self.N:
            raise ValueError("Action batches must match engine batch size")
        for env_idx in range(self.N):
            self._process_market_orders(env_idx, [actions_p0[env_idx], actions_p1[env_idx]])
            self._town_consume(env_idx)
        self.step_idx += 1
        self.day_idx = self.step_idx // 24
        self.hour_idx = self.step_idx % 24

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

    def _refresh_prices(self, env_idx: int) -> None:
        for product_idx, product in enumerate(self.PRODUCTS):
            inventory = int(self.market_inventory[env_idx, product_idx])
            cached = self._price_cache[product_idx].get(inventory)
            if cached is None:
                cached = self._market_price(product, inventory)
                self._price_cache[product_idx][inventory] = cached
            self.market_prices[env_idx, product_idx] = cached

    def _hire_cost(self, hires_today: int) -> int:
        a, b = 1, 1
        for _ in range(hires_today):
            a, b = b, a + b
        return a

    def _spawn_hand(self, env_idx: int, player_idx: int) -> list[int]:
        shed_tiles = [(4, 4), (5, 4), (4, 5), (5, 5)]
        occupants = {tile: 0 for tile in shed_tiles}
        for pos in [self.farmers[env_idx, player_idx].astype(int).tolist(), *self.hands[env_idx][player_idx]]:
            pos_tuple = tuple(pos)
            if pos_tuple in occupants:
                occupants[pos_tuple] += 1
        best = sorted(occupants.items(), key=lambda item: (item[1], shed_tiles.index(item[0])))
        return list(best[0][0])

    def _do_hire(self, env_idx: int, player_idx: int) -> None:
        cost = self._hire_cost(int(self.hires_today[env_idx, player_idx]))
        if self.money[env_idx, player_idx] < cost:
            return
        self.money[env_idx, player_idx] -= cost
        self.hires_today[env_idx, player_idx] += 1
        self.hands[env_idx][player_idx].append(self._spawn_hand(env_idx, player_idx))
        self.private_inventories[env_idx][player_idx].append({})
        self.workers[env_idx, player_idx] = len(self.hands[env_idx][player_idx])

    def _shed_used(self, env_idx: int, player_idx: int) -> int:
        return int(sum(self.private_shed[env_idx][player_idx].values()))

    def _deposit_to_shed(self, env_idx: int, player_idx: int, item: str, qty: int) -> int:
        room = max(0, self.config.shed_capacity - self._shed_used(env_idx, player_idx))
        take = min(max(0, int(qty)), room)
        if take > 0:
            shed = self.private_shed[env_idx][player_idx]
            shed[item] = shed.get(item, 0) + take
        return take

    def _do_buy_land(self, env_idx: int, player_idx: int) -> None:
        unlocked_extra = len(self.unlocked_quadrants[env_idx][player_idx]) - 1
        if unlocked_extra >= len(self.LAND_PRICES):
            return
        cost = self.LAND_PRICES[unlocked_extra]
        if self.money[env_idx, player_idx] < cost:
            return
        self.money[env_idx, player_idx] -= cost
        quadrant = self.LAND_ORDER[unlocked_extra]
        self.unlocked_quadrants[env_idx][player_idx].append(quadrant)
        self.land_count[env_idx, player_idx] = len(self.unlocked_quadrants[env_idx][player_idx])
        for y in range(self.config.board_size):
            for x in range(self.config.board_size):
                tile_quadrant = ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
                if tile_quadrant == quadrant and self.tiles[env_idx][player_idx][y][x] == "LOCKED":
                    self.tiles[env_idx][player_idx][y][x] = None

    def _commit_market_unit(self, env_idx: int, player_idx: int, op: str, item: str, price: float) -> bool:
        product_idx = self.PRODUCT_INDEX.get(item, -1)
        if op == "SELL":
            shed = self.private_shed[env_idx][player_idx]
            if shed.get(item, 0) <= 0:
                return False
            shed[item] -= 1
            self.money[env_idx, player_idx] += price
            if price > 1 and product_idx >= 0:
                self.market_inventory[env_idx, product_idx] += 1
            return True
        if op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
            if self.money[env_idx, player_idx] < price or product_idx < 0:
                return False
            if self._shed_used(env_idx, player_idx) >= self.config.shed_capacity:
                return False
            self.money[env_idx, player_idx] -= price
            self._deposit_to_shed(env_idx, player_idx, item, 1)
            self.market_inventory[env_idx, product_idx] -= 1
            return True
        if op == "BUY_SEED" and item in self.CROP_SEED_COSTS:
            if self.money[env_idx, player_idx] < price:
                return False
            self.money[env_idx, player_idx] -= price
            self.seeds_private[env_idx][player_idx][item] += 1
            return True
        if op == "BUY_ANIMAL" and item in self.ANIMAL_COSTS:
            if self.money[env_idx, player_idx] < price:
                return False
            if self._shed_used(env_idx, player_idx) >= self.config.shed_capacity:
                return False
            self.money[env_idx, player_idx] -= price
            self._deposit_to_shed(env_idx, player_idx, item, 1)
            return True
        return False

    def _parse_market_order(self, order: Any) -> dict[str, Any] | None:
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

    def _process_market_orders(self, env_idx: int, actions: list[dict[str, Any]]) -> None:
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
                    self._do_hire(env_idx, player_idx)
                    order_states[player_idx] = None
                elif order_state["type"] == "BUY_LAND":
                    self._do_buy_land(env_idx, player_idx)
                    order_states[player_idx] = None

            while True:
                quoted = [None, None]
                for player_idx, order_state in enumerate(order_states):
                    if order_state is None or order_state.get("remaining", 0) <= 0:
                        continue
                    op = order_state["type"]
                    item = order_state["item"]
                    product_idx = self.PRODUCT_INDEX.get(item, -1)
                    if op == "SELL" and product_idx >= 0:
                        quoted[player_idx] = (op, item, self._market_price(item, self.market_inventory[env_idx, product_idx]), order_state)
                    elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                        quoted[player_idx] = (op, item, self._market_price(item, self.market_inventory[env_idx, product_idx] - 1), order_state)
                    elif op == "BUY_SEED" and item in self.CROP_SEED_COSTS:
                        quoted[player_idx] = (op, item, float(self.CROP_SEED_COSTS[item]), order_state)
                    elif op == "BUY_ANIMAL" and item in self.ANIMAL_COSTS:
                        quoted[player_idx] = (op, item, float(self.ANIMAL_COSTS[item]), order_state)
                    else:
                        order_states[player_idx] = None

                if all(item is None for item in quoted):
                    break

                committed_any = False
                for player_idx, quote in enumerate(quoted):
                    if quote is None:
                        continue
                    op, item, price, order_state = quote
                    if self._commit_market_unit(env_idx, player_idx, op, item, price):
                        order_state["remaining"] -= 1
                        committed_any = True
                    else:
                        order_states[player_idx] = None
                if not committed_any:
                    break

            self._refresh_prices(env_idx)

    def _town_consume(self, env_idx: int) -> None:
        inventory = self.market_inventory[env_idx]
        if self.step_idx % self.TOWN_SHOP_SELL_INTERVAL == 0:
            for shop_name in self.town_shops[env_idx]:
                products = self.SHOPS[shop_name]
                multiplier = 2 if len(products) == 1 else 1
                for product in products:
                    inventory[self.PRODUCT_INDEX[product]] -= multiplier
        if self.step_idx % 24 == 0:
            for product in self.TOWN_CENTER_PRODUCTS:
                inventory[self.PRODUCT_INDEX[product]] -= 1
        self._refresh_prices(env_idx)

    def step(self, actions_p0: list[dict[str, Any]], actions_p1: list[dict[str, Any]]) -> np.ndarray:
        if len(actions_p0) != self.N or len(actions_p1) != self.N:
            raise ValueError("Action batches must match engine batch size")
        for env_idx in range(self.N):
            self._produce(env_idx)
            actions = [actions_p0[env_idx], actions_p1[env_idx]]
            for player_idx, action in enumerate(actions):
                if not isinstance(action, dict):
                    continue
                self._apply_unit_action(env_idx, player_idx, 0, action.get("farmer", ["PASS"]))
                hands_actions = action.get("hands", [])
                if isinstance(hands_actions, list):
                    for hand_idx, hand_action in enumerate(hands_actions):
                        self._apply_unit_action(env_idx, player_idx, hand_idx + 1, hand_action)
            self._process_market_orders(env_idx, actions)
            self._town_consume(env_idx)
            for player_idx in range(2):
                if self.plant_tiles[env_idx, player_idx] > 0:
                    self._decay_plants(env_idx, player_idx)
            if (self.step_idx + 1) % self.STEPS_PER_DAY == 0:
                self._end_of_day(env_idx)
        self.step_idx += 1
        self.day_idx = self.step_idx // self.STEPS_PER_DAY
        self.hour_idx = self.step_idx % self.STEPS_PER_DAY
        return self.money.copy()

    def _produce(self, env_idx: int) -> None:
        milk_idx = self.PRODUCT_INDEX["MILK"]
        wool_idx = self.PRODUCT_INDEX["WOOL"]
        if self.step_idx % 6 == 0 and self.step_idx > 0:
            self.public_inventory[env_idx, :, milk_idx] += self.active_cows[env_idx].astype(np.float64)
        if self.step_idx % 72 == 0 and self.step_idx > 0:
            self.public_inventory[env_idx, :, wool_idx] += self.active_sheep[env_idx].astype(np.float64) * 2.0

    def _unit_position(self, env_idx: int, player_idx: int, unit_idx: int) -> list[int] | None:
        if unit_idx == 0:
            return self.farmers[env_idx, player_idx].astype(int).tolist()
        hand_idx = unit_idx - 1
        if 0 <= hand_idx < len(self.hands[env_idx][player_idx]):
            return self.hands[env_idx][player_idx][hand_idx]
        return None

    def _set_unit_position(self, env_idx: int, player_idx: int, unit_idx: int, pos: list[int]) -> None:
        if unit_idx == 0:
            self.farmers[env_idx, player_idx] = pos
        else:
            self.hands[env_idx][player_idx][unit_idx - 1] = pos

    def _unit_inventory(self, env_idx: int, player_idx: int, unit_idx: int) -> dict[str, int]:
        inventories = self.private_inventories[env_idx][player_idx]
        while len(inventories) <= unit_idx:
            inventories.append({})
        return inventories[unit_idx]

    def _is_shed_adjacent(self, pos: list[int]) -> bool:
        return tuple(pos) in {(4, 4), (5, 4), (4, 5), (5, 5)}

    def _take_inventory(self, inventory: dict[str, int], item: str, qty: int = 1) -> bool:
        if inventory.get(item, 0) < qty:
            return False
        inventory[item] -= qty
        if inventory[item] == 0:
            del inventory[item]
        return True

    def _new_animal(self, item: str) -> dict[str, Any]:
        return {
            "kind": "PASTURE" if item in ("COW", "SHEEP") else "COOP",
            "animal": item,
            "placed_day": self.day_idx,
            "yield_units": 0,
            "fed_today": False,
            "cared_today": False,
            "fertilizer_available": False,
            "consecutive_unfed": 0,
            "pending_care_bonus": 0,
        }

    def _new_plant(self, crop: str) -> dict[str, Any]:
        crop_data = self.CROP_DATA[crop]
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

    def _apply_unit_action(self, env_idx: int, player_idx: int, unit_idx: int, action: Any) -> None:
        if not isinstance(action, list) or not action:
            return
        pos = self._unit_position(env_idx, player_idx, unit_idx)
        if pos is None:
            return
        op = action[0]
        moves = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
        if op in moves:
            dx, dy = moves[op]
            next_pos = [pos[0] + dx, pos[1] + dy]
            if 0 <= next_pos[0] < self.config.board_size and 0 <= next_pos[1] < self.config.board_size:
                self._set_unit_position(env_idx, player_idx, unit_idx, next_pos)
            return
        if op == "PASS":
            return

        fx, fy = pos
        tile = self.tiles[env_idx][player_idx][fy][fx]
        inventory = self._unit_inventory(env_idx, player_idx, unit_idx)

        if op == "DROP":
            if not self._is_shed_adjacent(pos):
                return
            for item, qty in list(inventory.items()):
                if qty > 0:
                    self._deposit_to_shed(env_idx, player_idx, item, qty)
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
            shed = self.private_shed[env_idx][player_idx]
            qty = min(max(0, qty), shed.get(item, 0))
            if qty <= 0:
                return
            shed[item] -= qty
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
                    self.tiles[env_idx][player_idx][fy][fx] = self._new_animal(item)
                    self.animal_tiles[env_idx, player_idx] += 1
            elif self._is_shed_adjacent(pos):
                try:
                    qty = int(action[2]) if len(action) >= 3 else 1
                except (TypeError, ValueError):
                    return
                qty = min(max(0, qty), inventory.get(item, 0))
                deposited = self._deposit_to_shed(env_idx, player_idx, item, qty)
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
            if crop not in self.CROP_DATA or tile is not None or self.seeds_private[env_idx][player_idx].get(crop, 0) <= 0:
                return
            self.seeds_private[env_idx][player_idx][crop] -= 1
            self.tiles[env_idx][player_idx][fy][fx] = self._new_plant(crop)
            self.plant_tiles[env_idx, player_idx] += 1
            return
        if op == "WATER":
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
                tile["watered_today"] = True
                crop_data = self.CROP_DATA[tile["crop"]]
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
                crop_data = self.CROP_DATA[tile["crop"]]
                if self.day_idx - tile["planted_day"] < crop_data["first_yield_day"]:
                    return
                units = int(tile["yield_units"])
                tile["yield_units"] = 0
                inventory[tile["crop"]] = inventory.get(tile["crop"], 0) + units
                if not crop_data["ongoing"]:
                    self.tiles[env_idx][player_idx][fy][fx] = None
                    self.plant_tiles[env_idx, player_idx] = max(0, self.plant_tiles[env_idx, player_idx] - 1)
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
                if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                    self.plant_tiles[env_idx, player_idx] = max(0, self.plant_tiles[env_idx, player_idx] - 1)
                self.tiles[env_idx][player_idx][fy][fx] = None
            return
        if op == "BUILD_PASTURE" and tile is None:
            self.tiles[env_idx][player_idx][fy][fx] = {"kind": "PASTURE"}
            return
        if op == "BUILD_COOP" and tile is None:
            self.tiles[env_idx][player_idx][fy][fx] = {"kind": "COOP"}
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

    def _refresh_active_animals(self, env_idx: int, player_idx: int) -> None:
        cows = 0
        sheep = 0
        for row in self.tiles[env_idx][player_idx]:
            for tile in row:
                if isinstance(tile, dict) and tile.get("animal") == "COW":
                    cows += 1
                elif isinstance(tile, dict) and tile.get("animal") == "SHEEP":
                    sheep += 1
        self.active_cows[env_idx, player_idx] = cows
        self.active_sheep[env_idx, player_idx] = sheep

    def _daily_refresh_plants(self, env_idx: int, player_idx: int) -> None:
        if self.plant_tiles[env_idx, player_idx] <= 0:
            return
        next_day = self.day_idx + 1
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
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
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}
                    self.plant_tiles[env_idx, player_idx] = max(0, self.plant_tiles[env_idx, player_idx] - 1)
                    continue
                crop_data = self.CROP_DATA[tile["crop"]]
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

    def _decay_plants(self, env_idx: int, player_idx: int) -> None:
        if self.plant_tiles[env_idx, player_idx] <= 0:
            return
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
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
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}
                    self.plant_tiles[env_idx, player_idx] = max(0, self.plant_tiles[env_idx, player_idx] - 1)

    def _daily_refresh_animals(self, env_idx: int, player_idx: int) -> None:
        if self.animal_tiles[env_idx, player_idx] <= 0:
            return
        next_day = self.day_idx + 1
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or "animal" not in tile:
                    continue
                if tile.get("fed_today", False):
                    tile["consecutive_unfed"] = 0
                else:
                    tile["consecutive_unfed"] = tile.get("consecutive_unfed", 0) + 1
                if tile["consecutive_unfed"] >= 2:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "PASTURE" if tile["animal"] in ("COW", "SHEEP") else "COOP"}
                    self.animal_tiles[env_idx, player_idx] = max(0, self.animal_tiles[env_idx, player_idx] - 1)
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

    def _spawn_weeds(self, env_idx: int, player_idx: int, rng: Any) -> None:
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
            for x, tile in enumerate(row):
                if tile is None and rng.random() < self.WEED_SPAWN_CHANCE:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}

    def _drop_inventories_to_shed(self, env_idx: int, player_idx: int) -> None:
        for inventory in self.private_inventories[env_idx][player_idx]:
            for item, qty in list(inventory.items()):
                if qty > 0:
                    self._deposit_to_shed(env_idx, player_idx, item, qty)
                del inventory[item]

    def _end_of_day(self, env_idx: int) -> None:
        import random

        rng = random.Random((int(self.seeds[env_idx]) * 1_000_003) ^ self.day_idx)
        for player_idx in range(2):
            self._daily_refresh_plants(env_idx, player_idx)
            self._daily_refresh_animals(env_idx, player_idx)
            self._spawn_weeds(env_idx, player_idx, rng)
            self._drop_inventories_to_shed(env_idx, player_idx)
            self.farmers[env_idx, player_idx] = [4, 4]
            self.hands[env_idx][player_idx] = []
            self.workers[env_idx, player_idx] = 0
            self.hires_today[env_idx, player_idx] = 0
            self.private_inventories[env_idx][player_idx] = [{}]
        next_day = self.day_idx + 1
        if (
            next_day > 0
            and next_day % self.TOWN_SHOP_UNLOCK_INTERVAL == 0
            and len(self.town_shops[env_idx]) < self.MAX_SHOP_INSTANCES
        ):
            self.town_shops[env_idx].append(rng.choice(sorted(self.SHOPS)))
