"""Torch/CUDA numeric backend for Step 3H-8.

This is not a full simulator yet. It ports the parity-correct numeric reset and
market/order transition from ``CorrectedVectorPairedEngine`` onto CUDA tensors,
while keeping Python action parsing and small object projections at the edge.
Step 3H-8B adds CUDA-resident physical-state mirrors; later gates will move the
physical transition interpreter itself onto those tensors.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import torch

from apex_next.gpu_engine.paired_gpu_v25.corrected_vector_engine import CorrectedVectorPairedEngine


class CorrectedCudaPairedEngine:
    PRODUCTS = CorrectedVectorPairedEngine.PRODUCTS
    CROPS = CorrectedVectorPairedEngine.CROPS
    ANIMALS = CorrectedVectorPairedEngine.ANIMALS
    PRODUCT_INDEX = CorrectedVectorPairedEngine.PRODUCT_INDEX
    BASE_PRICES_LIST = [25.0, 35.0, 60.0, 120.0, 250.0, 50.0, 160.0, 200.0, 100.0]
    MARKET_I0 = CorrectedVectorPairedEngine.MARKET_I0
    PRICE_FLOOR = CorrectedVectorPairedEngine.PRICE_FLOOR
    LAND_ORDER = CorrectedVectorPairedEngine.LAND_ORDER
    LAND_PRICES = CorrectedVectorPairedEngine.LAND_PRICES
    TOWN_CENTER_PRODUCTS = CorrectedVectorPairedEngine.TOWN_CENTER_PRODUCTS
    TOWN_SHOP_UNLOCK_INTERVAL = CorrectedVectorPairedEngine.TOWN_SHOP_UNLOCK_INTERVAL
    TOWN_SHOP_SELL_INTERVAL = CorrectedVectorPairedEngine.TOWN_SHOP_SELL_INTERVAL
    MAX_SHOP_INSTANCES = CorrectedVectorPairedEngine.MAX_SHOP_INSTANCES
    SHOPS = CorrectedVectorPairedEngine.SHOPS
    MARKET_PARAMS = CorrectedVectorPairedEngine.MARKET_PARAMS
    ANIMAL_COSTS = CorrectedVectorPairedEngine.ANIMAL_COSTS
    CROP_SEED_COSTS = CorrectedVectorPairedEngine.CROP_SEED_COSTS
    CROP_DATA = CorrectedVectorPairedEngine.CROP_DATA
    STEPS_PER_DAY = CorrectedVectorPairedEngine.STEPS_PER_DAY
    ANIMAL_DATA = {
        "GOOSE": {"first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
        "COW": {"first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
        "SHEEP": {"first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
    }
    SHED_CAPACITY = 100
    BOARD_SIZE = 10
    MAX_HANDS = 32
    TILE_EMPTY = 0
    TILE_LOCKED = 1
    TILE_WEED = 2
    TILE_PLANT = 3
    TILE_PASTURE = 4
    TILE_COOP = 5
    TILE_ANIMAL = 6
    ITEM_INDEX = {item: idx for idx, item in enumerate(PRODUCTS + ANIMALS)}
    CROP_INDEX = {crop: idx + 1 for idx, crop in enumerate(CROPS)}
    ANIMAL_INDEX = {animal: idx + 1 for idx, animal in enumerate(ANIMALS)}
    TERMINAL_STEP = 719
    REWARD_NORMALIZER = 100000.0

    def __init__(self, batch_size: int = 1, base_seed: int = 39000, device: str | torch.device | None = None) -> None:
        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(device)
        self.N = int(batch_size)
        self.base_seed = int(base_seed)
        self.base_prices = torch.tensor(self.BASE_PRICES_LIST, dtype=torch.float64, device=self.device)
        self.reset(list(range(self.base_seed, self.base_seed + self.N)))

    @property
    def actual_cuda_used(self) -> bool:
        return self.money.is_cuda and self.market_prices.is_cuda and self.tile_kind.is_cuda

    def physical_tensor_signature(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        hand_count = int(self.hand_active[env_idx, player_idx].sum().item())
        return {
            "tile_kind_counts": self._tensor_counts(self.tile_kind[env_idx, player_idx], 0, self.TILE_ANIMAL),
            "tile_item_sum": int(self.tile_item[env_idx, player_idx].sum().item()),
            "tile_yield_sum": int(self.tile_yield[env_idx, player_idx].sum().item()),
            "tile_flags_sum": int(self.tile_flags[env_idx, player_idx].sum().item()),
            "hand_count": hand_count,
            "hand_positions": self.hand_pos[env_idx, player_idx, :hand_count].detach().cpu().to(torch.int16).tolist(),
            "shed": self.private_shed_tensor[env_idx, player_idx].detach().cpu().to(torch.int16).tolist(),
            "seeds": self.seed_tensor[env_idx, player_idx].detach().cpu().to(torch.int16).tolist(),
            "devices": {
                "tile_kind": str(self.tile_kind.device),
                "hand_pos": str(self.hand_pos.device),
                "private_shed": str(self.private_shed_tensor.device),
                "seeds": str(self.seed_tensor.device),
            },
        }

    def _tensor_counts(self, tensor: torch.Tensor, start: int, end: int) -> dict[str, int]:
        return {
            str(value): int((tensor == value).sum().item())
            for value in range(start, end + 1)
        }

    def reset(self, seeds: list[int] | None = None) -> None:
        if seeds is None:
            seeds = list(range(self.base_seed, self.base_seed + self.N))
        self.N = len(seeds)
        self.seeds = torch.tensor(seeds, dtype=torch.int64, device=self.device)
        self.step_idx = 0
        self.day_idx = 0
        self.hour_idx = 0
        self.money = torch.full((self.N, 2), 3000.0, dtype=torch.float64, device=self.device)
        self.money_mirror = [[3000.0, 3000.0] for _ in range(self.N)]
        self.land_count = torch.ones((self.N, 2), dtype=torch.int32, device=self.device)
        self.workers = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.hires_today = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.hires_today_mirror = [[0, 0] for _ in range(self.N)]
        self.active_cows = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.active_sheep = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.plant_tiles = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.animal_tiles = torch.zeros((self.N, 2), dtype=torch.int32, device=self.device)
        self.farmers = torch.full((self.N, 2, 2), 4, dtype=torch.int32, device=self.device)
        self.public_inventory = torch.zeros((self.N, 2, len(self.PRODUCTS)), dtype=torch.float64, device=self.device)
        self.market_inventory = torch.full((self.N, len(self.PRODUCTS)), self.MARKET_I0, dtype=torch.int32, device=self.device)
        self.market_inventory_mirror = [[int(self.MARKET_I0) for _ in self.PRODUCTS] for _ in range(self.N)]
        self.market_prices = self.base_prices.repeat(self.N, 1).clone()
        self.market_prices_mirror = [list(self.BASE_PRICES_LIST) for _ in range(self.N)]

        self.hands: list[list[list[list[int]]]] = [[[], []] for _ in range(self.N)]
        self.unlocked_quadrants: list[list[list[str]]] = [[["NW"], ["NW"]] for _ in range(self.N)]
        self.tiles = [[self._initial_tiles(), self._initial_tiles()] for _ in range(self.N)]
        self.private_shed = [
            [{item: 0 for item in self.PRODUCTS + self.ANIMALS} for _ in range(2)]
            for _ in range(self.N)
        ]
        self.private_inventories: list[list[list[dict[str, int]]]] = [[[{}], [{}]] for _ in range(self.N)]
        self.seeds_private = [
            [{crop: 0 for crop in self.CROPS} for _ in range(2)]
            for _ in range(self.N)
        ]
        self.town_shops: list[list[str]] = [[] for _ in range(self.N)]
        self._price_cache: list[dict[int, float]] = [dict() for _ in self.PRODUCTS]
        self._defer_physical_sync = False
        self._dirty_physical_sync: set[tuple[int, int]] = set()
        self._init_physical_tensors()
        self._sync_all_physical_tensors()

    def observation(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        opp_idx = 1 - player_idx
        return {
            "step": self.step_idx,
            "day": self.day_idx,
            "hour": self.hour_idx,
            "player": player_idx,
            "farms": [self._farm(env_idx, player_idx), self._farm(env_idx, opp_idx)],
            "market": {
                "inventory": {
                    product: int(self.market_inventory_mirror[env_idx][idx])
                    for idx, product in enumerate(self.PRODUCTS)
                },
                "prices": {
                    product: float(self.market_prices[env_idx, idx].item())
                    for idx, product in enumerate(self.PRODUCTS)
                },
            },
            "town": {"unlocked_shops": list(self.town_shops[env_idx])},
        }

    def _init_physical_tensors(self) -> None:
        shape = (self.N, 2, self.BOARD_SIZE, self.BOARD_SIZE)
        self.tile_kind = torch.zeros(shape, dtype=torch.int16, device=self.device)
        self.tile_item = torch.zeros(shape, dtype=torch.int16, device=self.device)
        self.tile_yield = torch.zeros(shape, dtype=torch.int16, device=self.device)
        self.tile_planted_day = torch.full(shape, -1, dtype=torch.int16, device=self.device)
        self.tile_placed_day = torch.full(shape, -1, dtype=torch.int16, device=self.device)
        self.tile_flags = torch.zeros(shape, dtype=torch.int16, device=self.device)
        self.hand_active = torch.zeros((self.N, 2, self.MAX_HANDS), dtype=torch.bool, device=self.device)
        self.hand_pos = torch.full((self.N, 2, self.MAX_HANDS, 2), -1, dtype=torch.int16, device=self.device)
        self.private_shed_tensor = torch.zeros((self.N, 2, len(self.ITEM_INDEX)), dtype=torch.int16, device=self.device)
        self.seed_tensor = torch.zeros((self.N, 2, len(self.CROPS)), dtype=torch.int16, device=self.device)

    def _sync_all_physical_tensors(self) -> None:
        for env_idx in range(self.N):
            for player_idx in range(2):
                self._sync_physical_tensors_now(env_idx, player_idx)
        self._dirty_physical_sync.clear()

    def _sync_physical_tensors(self, env_idx: int, player_idx: int) -> None:
        if self._defer_physical_sync:
            self._dirty_physical_sync.add((env_idx, player_idx))
            return
        self._sync_physical_tensors_now(env_idx, player_idx)

    def _sync_physical_tensors_now(self, env_idx: int, player_idx: int) -> None:
        # Encode the object edge into host-side numeric buffers first. Scalar
        # writes into CUDA tensors launch one tiny operation per field/tile.
        tile_kind: list[list[int]] = []
        tile_item: list[list[int]] = []
        tile_yield: list[list[int]] = []
        tile_planted_day: list[list[int]] = []
        tile_placed_day: list[list[int]] = []
        tile_flags: list[list[int]] = []
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
            kind_row: list[int] = []
            item_row: list[int] = []
            yield_row: list[int] = []
            planted_row: list[int] = []
            placed_row: list[int] = []
            flags_row: list[int] = []
            for x, tile in enumerate(row):
                kind, item, yield_units, planted_day, placed_day, flags = self._encode_tile(tile)
                kind_row.append(kind)
                item_row.append(item)
                yield_row.append(yield_units)
                planted_row.append(planted_day)
                placed_row.append(placed_day)
                flags_row.append(flags)
            tile_kind.append(kind_row)
            tile_item.append(item_row)
            tile_yield.append(yield_row)
            tile_planted_day.append(planted_row)
            tile_placed_day.append(placed_row)
            tile_flags.append(flags_row)

        def copy_field(target: torch.Tensor, values: list[list[int]], dtype: torch.dtype) -> None:
            source = torch.tensor(values, dtype=dtype, device=self.device)
            target[env_idx, player_idx].copy_(source)

        copy_field(self.tile_kind, tile_kind, torch.int16)
        copy_field(self.tile_item, tile_item, torch.int16)
        copy_field(self.tile_yield, tile_yield, torch.int16)
        copy_field(self.tile_planted_day, tile_planted_day, torch.int16)
        copy_field(self.tile_placed_day, tile_placed_day, torch.int16)
        copy_field(self.tile_flags, tile_flags, torch.int16)

        hand_active = [False] * self.MAX_HANDS
        hand_pos = [[-1, -1] for _ in range(self.MAX_HANDS)]
        for hand_idx, pos in enumerate(self.hands[env_idx][player_idx][: self.MAX_HANDS]):
            hand_active[hand_idx] = True
            hand_pos[hand_idx] = [int(pos[0]), int(pos[1])]
        self.hand_active[env_idx, player_idx].copy_(torch.tensor(hand_active, dtype=torch.bool, device=self.device))
        self.hand_pos[env_idx, player_idx].copy_(torch.tensor(hand_pos, dtype=torch.int16, device=self.device))

        shed_values = [0] * len(self.ITEM_INDEX)
        for item, count in self.private_shed[env_idx][player_idx].items():
            item_idx = self.ITEM_INDEX.get(item)
            if item_idx is not None:
                shed_values[item_idx] = int(count)
        self.private_shed_tensor[env_idx, player_idx].copy_(torch.tensor(shed_values, dtype=torch.int16, device=self.device))

        seed_values = [int(self.seeds_private[env_idx][player_idx].get(crop, 0)) for crop in self.CROPS]
        self.seed_tensor[env_idx, player_idx].copy_(torch.tensor(seed_values, dtype=torch.int16, device=self.device))

    def _flush_deferred_physical_tensors(self) -> None:
        dirty = sorted(self._dirty_physical_sync)
        self._dirty_physical_sync.clear()
        for env_idx, player_idx in dirty:
            self._sync_physical_tensors_now(env_idx, player_idx)

    def _encode_tile(self, tile: Any) -> tuple[int, int, int, int, int, int]:
        if tile is None:
            return self.TILE_EMPTY, 0, 0, -1, -1, 0
        if tile == "LOCKED":
            return self.TILE_LOCKED, 0, 0, -1, -1, 0
        if isinstance(tile, dict) and tile.get("kind") == "WEED":
            return self.TILE_WEED, 0, 0, -1, -1, 0
        if isinstance(tile, dict) and tile.get("kind") == "PASTURE":
            return self.TILE_PASTURE, 0, 0, -1, -1, 0
        if isinstance(tile, dict) and tile.get("kind") == "COOP":
            return self.TILE_COOP, 0, 0, -1, -1, 0
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            flags = 0
            flags |= 1 if tile.get("watered_today", False) else 0
            flags |= 2 if tile.get("fertilized_until_day", -1) >= self.day_idx else 0
            return (
                self.TILE_PLANT,
                self.CROP_INDEX.get(tile.get("crop"), 0),
                int(tile.get("yield_units", 0)),
                int(tile.get("planted_day", -1)),
                -1,
                flags,
            )
        if isinstance(tile, dict) and "animal" in tile:
            flags = 0
            flags |= 1 if tile.get("fed_today", False) else 0
            flags |= 2 if tile.get("cared_today", False) else 0
            flags |= 4 if tile.get("fertilizer_available", False) else 0
            return (
                self.TILE_ANIMAL,
                self.ANIMAL_INDEX.get(tile.get("animal"), 0),
                int(tile.get("yield_units", 0)),
                -1,
                int(tile.get("placed_day", -1)),
                flags,
            )
        return self.TILE_EMPTY, 0, 0, -1, -1, 0

    def _farm(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        return {
            "money": float(self.money_mirror[env_idx][player_idx]),
            "land": int(self.land_count[env_idx, player_idx].item()),
            "tiles": copy.deepcopy(self.tiles[env_idx][player_idx]),
            "farmer": self.farmers[env_idx, player_idx].detach().cpu().to(torch.int32).tolist(),
            "hands": copy.deepcopy(self.hands[env_idx][player_idx]),
            "unlocked_quadrants": list(self.unlocked_quadrants[env_idx][player_idx]),
            "inventory": {
                product: float(self.public_inventory[env_idx, player_idx, idx].item())
                for idx, product in enumerate(self.PRODUCTS)
            },
        }

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

    def private_observation(self, env_idx: int, player_idx: int) -> dict[str, Any]:
        return {
            "shed": copy.deepcopy(self.private_shed[env_idx][player_idx]),
            "inventories": copy.deepcopy(self.private_inventories[env_idx][player_idx]),
            "seeds": copy.deepcopy(self.seeds_private[env_idx][player_idx]),
        }

    def step_market_only(self, actions_p0: list[dict[str, Any]], actions_p1: list[dict[str, Any]]) -> None:
        if len(actions_p0) != self.N or len(actions_p1) != self.N:
            raise ValueError("Action batches must match engine batch size")
        for env_idx in range(self.N):
            self._process_market_orders(env_idx, [actions_p0[env_idx], actions_p1[env_idx]])
            self._town_consume(env_idx)
        self.step_idx += 1
        self.day_idx = self.step_idx // 24
        self.hour_idx = self.step_idx % 24

    def step_integrated(self, actions_p0: list[dict[str, Any]], actions_p1: list[dict[str, Any]]) -> torch.Tensor:
        """Apply the full non-terminal transition path for Step 3H-8H."""

        if len(actions_p0) != self.N or len(actions_p1) != self.N:
            raise ValueError("Action batches must match engine batch size")
        previous_defer = self._defer_physical_sync
        self._defer_physical_sync = True
        try:
            for env_idx in range(self.N):
                self._produce(env_idx)
                actions = [actions_p0[env_idx], actions_p1[env_idx]]
                for player_idx, action in enumerate(actions):
                    if not isinstance(action, dict):
                        continue
                    self._apply_unit_action_physical_slice(env_idx, player_idx, 0, action.get("farmer", ["PASS"]))
                    hands_actions = action.get("hands", [])
                    if isinstance(hands_actions, list):
                        for hand_idx, hand_action in enumerate(hands_actions):
                            self._apply_unit_action_physical_slice(env_idx, player_idx, hand_idx + 1, hand_action)
                self._process_market_orders(env_idx, actions)
                self._town_consume(env_idx)
                for player_idx in range(2):
                    if int(self.plant_tiles[env_idx, player_idx].item()) > 0:
                        self._decay_plants(env_idx, player_idx)
                if (self.step_idx + 1) % self.STEPS_PER_DAY == 0:
                    self._end_of_day(env_idx)
            previous_day = self.day_idx
            self.step_idx += 1
            self.day_idx = self.step_idx // self.STEPS_PER_DAY
            self.hour_idx = self.step_idx % self.STEPS_PER_DAY
            self._defer_physical_sync = previous_defer
            if self.day_idx != previous_day:
                self._sync_all_physical_tensors()
            else:
                self._flush_deferred_physical_tensors()
        finally:
            self._defer_physical_sync = previous_defer
        return self.money.clone()

    def terminal_metrics(self, env_idx: int, player_idx: int = 0) -> dict[str, Any]:
        """Return terminal/reward metrics matching the corrected CPU reference.

        The parity reference and existing GPU screening engines use terminal
        Kaggriculture reward/MCV as final cash. Step 5 normalizes the player
        reward delta by 100000.0 for PPO.
        """

        if not 0 <= env_idx < self.N:
            raise IndexError(f"env_idx out of range: {env_idx}")
        if player_idx not in (0, 1):
            raise ValueError(f"player_idx must be 0 or 1, got {player_idx}")
        opponent_idx = 1 - player_idx
        terminal = self.step_idx >= self.TERMINAL_STEP
        player_mcvs = self.money[env_idx].detach().clone()
        own_mcv = float(player_mcvs[player_idx].item())
        opponent_mcv = float(player_mcvs[opponent_idx].item())
        raw_reward = own_mcv - opponent_mcv if terminal else 0.0
        if abs(float(player_mcvs[0].item()) - float(player_mcvs[1].item())) <= 1e-9:
            winner: int | None = None
        else:
            winner = int(torch.argmax(player_mcvs).item())
        return {
            "terminal": bool(terminal),
            "step": int(self.step_idx),
            "terminal_step": self.TERMINAL_STEP,
            "player_idx": int(player_idx),
            "our_mcv": own_mcv,
            "opponent_mcv": opponent_mcv,
            "player_mcvs": [float(value) for value in player_mcvs.detach().cpu().tolist()],
            "winner": winner,
            "raw_terminal_reward": float(raw_reward),
            "normalized_reward": float(raw_reward / self.REWARD_NORMALIZER),
            "reward_normalizer": self.REWARD_NORMALIZER,
            "valuation_source": "final_cash_matches_corrected_cpu_reference_and_existing_gpu_screeners",
        }

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

    def _cached_market_price(self, product_idx: int, inventory: int) -> float:
        cached = self._price_cache[product_idx].get(inventory)
        if cached is None:
            cached = self._market_price(self.PRODUCTS[product_idx], inventory)
            self._price_cache[product_idx][inventory] = cached
        return cached

    def _refresh_prices(self, env_idx: int) -> None:
        values = []
        for product_idx, _product in enumerate(self.PRODUCTS):
            inventory = int(self.market_inventory_mirror[env_idx][product_idx])
            values.append(self._cached_market_price(product_idx, inventory))
        if values != self.market_prices_mirror[env_idx]:
            self.market_prices_mirror[env_idx] = values
            self.market_prices[env_idx] = torch.tensor(values, dtype=torch.float64, device=self.device)

    def _hire_cost(self, hires_today: int) -> int:
        a, b = 1, 1
        for _ in range(hires_today):
            a, b = b, a + b
        return a

    def _spawn_hand(self, env_idx: int, player_idx: int) -> list[int]:
        shed_tiles = [(4, 4), (5, 4), (4, 5), (5, 5)]
        occupants = {tile: 0 for tile in shed_tiles}
        farmer = self.farmers[env_idx, player_idx].detach().cpu().to(torch.int32).tolist()
        for pos in [farmer, *self.hands[env_idx][player_idx]]:
            pos_tuple = tuple(pos)
            if pos_tuple in occupants:
                occupants[pos_tuple] += 1
        best = sorted(occupants.items(), key=lambda item: (item[1], shed_tiles.index(item[0])))
        return list(best[0][0])

    def _do_hire(self, env_idx: int, player_idx: int) -> None:
        cost = self._hire_cost(self.hires_today_mirror[env_idx][player_idx])
        if self.money_mirror[env_idx][player_idx] < cost:
            return
        self.money[env_idx, player_idx] -= cost
        self.money_mirror[env_idx][player_idx] -= cost
        self.hires_today[env_idx, player_idx] += 1
        self.hires_today_mirror[env_idx][player_idx] += 1
        self.hands[env_idx][player_idx].append(self._spawn_hand(env_idx, player_idx))
        self.private_inventories[env_idx][player_idx].append({})
        self.workers[env_idx, player_idx] = len(self.hands[env_idx][player_idx])
        self._sync_physical_tensors(env_idx, player_idx)

    def _shed_used(self, env_idx: int, player_idx: int) -> int:
        return int(sum(self.private_shed[env_idx][player_idx].values()))

    def _deposit_to_shed(self, env_idx: int, player_idx: int, item: str, qty: int) -> int:
        room = max(0, self.SHED_CAPACITY - self._shed_used(env_idx, player_idx))
        take = min(max(0, int(qty)), room)
        if take > 0:
            shed = self.private_shed[env_idx][player_idx]
            shed[item] = shed.get(item, 0) + take
            self._sync_physical_tensors(env_idx, player_idx)
        return take

    def _do_buy_land(self, env_idx: int, player_idx: int) -> None:
        unlocked_extra = len(self.unlocked_quadrants[env_idx][player_idx]) - 1
        if unlocked_extra >= len(self.LAND_PRICES):
            return
        cost = self.LAND_PRICES[unlocked_extra]
        if self.money_mirror[env_idx][player_idx] < cost:
            return
        self.money[env_idx, player_idx] -= cost
        self.money_mirror[env_idx][player_idx] -= cost
        quadrant = self.LAND_ORDER[unlocked_extra]
        self.unlocked_quadrants[env_idx][player_idx].append(quadrant)
        self.land_count[env_idx, player_idx] = len(self.unlocked_quadrants[env_idx][player_idx])
        for y in range(10):
            for x in range(10):
                tile_quadrant = ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
                if tile_quadrant == quadrant and self.tiles[env_idx][player_idx][y][x] == "LOCKED":
                    self.tiles[env_idx][player_idx][y][x] = None
        self._sync_physical_tensors(env_idx, player_idx)

    def _commit_market_unit(self, env_idx: int, player_idx: int, op: str, item: str, price: float) -> bool:
        product_idx = self.PRODUCT_INDEX.get(item, -1)
        if op == "SELL":
            shed = self.private_shed[env_idx][player_idx]
            if shed.get(item, 0) <= 0:
                return False
            shed[item] -= 1
            self.money[env_idx, player_idx] += price
            self.money_mirror[env_idx][player_idx] += price
            if price > 1 and product_idx >= 0:
                self.market_inventory[env_idx, product_idx] += 1
                self.market_inventory_mirror[env_idx][product_idx] += 1
            self._sync_physical_tensors(env_idx, player_idx)
            return True
        if op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
            if self.money_mirror[env_idx][player_idx] < price or product_idx < 0:
                return False
            if self._shed_used(env_idx, player_idx) >= self.SHED_CAPACITY:
                return False
            self.money[env_idx, player_idx] -= price
            self.money_mirror[env_idx][player_idx] -= price
            self._deposit_to_shed(env_idx, player_idx, item, 1)
            self.market_inventory[env_idx, product_idx] -= 1
            self.market_inventory_mirror[env_idx][product_idx] -= 1
            return True
        if op == "BUY_SEED" and item in self.CROP_SEED_COSTS:
            if self.money_mirror[env_idx][player_idx] < price:
                return False
            self.money[env_idx, player_idx] -= price
            self.money_mirror[env_idx][player_idx] -= price
            self.seeds_private[env_idx][player_idx][item] += 1
            self._sync_physical_tensors(env_idx, player_idx)
            return True
        if op == "BUY_ANIMAL" and item in self.ANIMAL_COSTS:
            if self.money_mirror[env_idx][player_idx] < price:
                return False
            if self._shed_used(env_idx, player_idx) >= self.SHED_CAPACITY:
                return False
            self.money[env_idx, player_idx] -= price
            self.money_mirror[env_idx][player_idx] -= price
            self._deposit_to_shed(env_idx, player_idx, item, 1)
            return True
        return False

    def step_physical_slice(self, actions_p0: list[dict[str, Any]], actions_p1: list[dict[str, Any]]) -> None:
        """Apply the 3H-8C physical action slice.

        This is a transition-port staging method for movement/carry/build/place.
        It intentionally excludes crop, animal lifecycle, production, market, and
        terminal updates.
        """

        if len(actions_p0) != self.N or len(actions_p1) != self.N:
            raise ValueError("Action batches must match engine batch size")
        for env_idx in range(self.N):
            for player_idx, action in enumerate([actions_p0[env_idx], actions_p1[env_idx]]):
                if not isinstance(action, dict):
                    continue
                self._apply_unit_action_physical_slice(env_idx, player_idx, 0, action.get("farmer", ["PASS"]))
                hands_actions = action.get("hands", [])
                if isinstance(hands_actions, list):
                    for hand_idx, hand_action in enumerate(hands_actions):
                        self._apply_unit_action_physical_slice(env_idx, player_idx, hand_idx + 1, hand_action)

    def _unit_position(self, env_idx: int, player_idx: int, unit_idx: int) -> list[int] | None:
        if unit_idx == 0:
            return self.farmers[env_idx, player_idx].detach().cpu().to(torch.int32).tolist()
        hand_idx = unit_idx - 1
        if 0 <= hand_idx < len(self.hands[env_idx][player_idx]):
            return self.hands[env_idx][player_idx][hand_idx]
        return None

    def _set_unit_position(self, env_idx: int, player_idx: int, unit_idx: int, pos: list[int]) -> None:
        if unit_idx == 0:
            self.farmers[env_idx, player_idx] = torch.tensor(pos, dtype=torch.int32, device=self.device)
        else:
            self.hands[env_idx][player_idx][unit_idx - 1] = pos
        self._sync_physical_tensors(env_idx, player_idx)

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

    def _produce(self, env_idx: int) -> None:
        milk_idx = self.PRODUCT_INDEX["MILK"]
        wool_idx = self.PRODUCT_INDEX["WOOL"]
        if self.step_idx % 6 == 0 and self.step_idx > 0:
            self.public_inventory[env_idx, :, milk_idx] += self.active_cows[env_idx].to(torch.float64)
        if self.step_idx % 72 == 0 and self.step_idx > 0:
            self.public_inventory[env_idx, :, wool_idx] += self.active_sheep[env_idx].to(torch.float64) * 2.0

    def daily_crop_lifecycle_slice(self) -> None:
        """Apply only daily crop refresh across the batch for 3H-8F."""

        for env_idx in range(self.N):
            for player_idx in range(2):
                self._daily_refresh_plants(env_idx, player_idx)

    def crop_decay_slice(self) -> None:
        """Apply only crop lifespan decay across the batch for 3H-8F."""

        for env_idx in range(self.N):
            for player_idx in range(2):
                self._decay_plants(env_idx, player_idx)

    def daily_animal_lifecycle_slice(self) -> None:
        """Apply only daily animal refresh across the batch for 3H-8G."""

        for env_idx in range(self.N):
            for player_idx in range(2):
                self._daily_refresh_animals(env_idx, player_idx)

    def _daily_refresh_plants(self, env_idx: int, player_idx: int) -> None:
        if int(self.plant_tiles[env_idx, player_idx].item()) <= 0:
            return
        next_day = self.day_idx + 1
        changed = False
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
                changed = True
                if tile["consecutive_unwatered"] >= 2:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}
                    self.plant_tiles[env_idx, player_idx] = torch.maximum(
                        self.plant_tiles[env_idx, player_idx] - 1,
                        torch.tensor(0, dtype=torch.int32, device=self.device),
                    )
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
        if changed:
            self._sync_physical_tensors(env_idx, player_idx)

    def _daily_refresh_animals(self, env_idx: int, player_idx: int) -> None:
        if int(self.animal_tiles[env_idx, player_idx].item()) <= 0:
            return
        next_day = self.day_idx + 1
        changed = False
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or "animal" not in tile:
                    continue
                if tile.get("fed_today", False):
                    tile["consecutive_unfed"] = 0
                else:
                    tile["consecutive_unfed"] = tile.get("consecutive_unfed", 0) + 1
                changed = True
                if tile["consecutive_unfed"] >= 2:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "PASTURE" if tile["animal"] in ("COW", "SHEEP") else "COOP"}
                    self.animal_tiles[env_idx, player_idx] = torch.maximum(
                        self.animal_tiles[env_idx, player_idx] - 1,
                        torch.tensor(0, dtype=torch.int32, device=self.device),
                    )
                    continue
                animal_data = self.ANIMAL_DATA[tile["animal"]]
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
        if changed:
            self._sync_physical_tensors(env_idx, player_idx)

    def _spawn_weeds(self, env_idx: int, player_idx: int, rng: Any) -> None:
        changed = False
        for y, row in enumerate(self.tiles[env_idx][player_idx]):
            for x, tile in enumerate(row):
                if tile is None and rng.random() < CorrectedVectorPairedEngine.WEED_SPAWN_CHANCE:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}
                    changed = True
        if changed:
            self._sync_physical_tensors(env_idx, player_idx)

    def _drop_inventories_to_shed(self, env_idx: int, player_idx: int) -> None:
        changed = False
        for inventory in self.private_inventories[env_idx][player_idx]:
            for item, qty in list(inventory.items()):
                if qty > 0:
                    self._deposit_to_shed(env_idx, player_idx, item, qty)
                    changed = True
                del inventory[item]
        if changed:
            self._sync_physical_tensors(env_idx, player_idx)

    def _end_of_day(self, env_idx: int) -> None:
        import random

        rng = random.Random((int(self.seeds[env_idx].item()) * 1_000_003) ^ self.day_idx)
        for player_idx in range(2):
            self._daily_refresh_plants(env_idx, player_idx)
            self._daily_refresh_animals(env_idx, player_idx)
            self._spawn_weeds(env_idx, player_idx, rng)
            self._drop_inventories_to_shed(env_idx, player_idx)
            self.farmers[env_idx, player_idx] = torch.tensor([4, 4], dtype=torch.int32, device=self.device)
            self.hands[env_idx][player_idx] = []
            self.workers[env_idx, player_idx] = 0
            self.hires_today[env_idx, player_idx] = 0
            self.hires_today_mirror[env_idx][player_idx] = 0
            self.private_inventories[env_idx][player_idx] = [{}]
            self._sync_physical_tensors(env_idx, player_idx)
        next_day = self.day_idx + 1
        if (
            next_day > 0
            and next_day % self.TOWN_SHOP_UNLOCK_INTERVAL == 0
            and len(self.town_shops[env_idx]) < self.MAX_SHOP_INSTANCES
        ):
            self.town_shops[env_idx].append(rng.choice(sorted(self.SHOPS)))

    def _decay_plants(self, env_idx: int, player_idx: int) -> None:
        if int(self.plant_tiles[env_idx, player_idx].item()) <= 0:
            return
        changed = False
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
                changed = True
                if tile["yield_units"] <= 0:
                    self.tiles[env_idx][player_idx][y][x] = {"kind": "WEED"}
                    self.plant_tiles[env_idx, player_idx] = torch.maximum(
                        self.plant_tiles[env_idx, player_idx] - 1,
                        torch.tensor(0, dtype=torch.int32, device=self.device),
                    )
        if changed:
            self._sync_physical_tensors(env_idx, player_idx)

    def _apply_unit_action_physical_slice(self, env_idx: int, player_idx: int, unit_idx: int, action: Any) -> None:
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
            if 0 <= next_pos[0] < self.BOARD_SIZE and 0 <= next_pos[1] < self.BOARD_SIZE:
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
            self._sync_physical_tensors(env_idx, player_idx)
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
            self._sync_physical_tensors(env_idx, player_idx)
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
                    self._sync_physical_tensors(env_idx, player_idx)
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
                    self._sync_physical_tensors(env_idx, player_idx)
            return
        if tile == "LOCKED":
            return
        if op == "BUILD_PASTURE" and tile is None:
            self.tiles[env_idx][player_idx][fy][fx] = {"kind": "PASTURE"}
            self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "BUILD_COOP" and tile is None:
            self.tiles[env_idx][player_idx][fy][fx] = {"kind": "COOP"}
            self._sync_physical_tensors(env_idx, player_idx)
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
            self._sync_physical_tensors(env_idx, player_idx)
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
                self._sync_physical_tensors(env_idx, player_idx)
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
                self.plant_tiles[env_idx, player_idx] = torch.maximum(
                    self.plant_tiles[env_idx, player_idx] - 1,
                    torch.tensor(0, dtype=torch.int32, device=self.device),
                )
                self._sync_physical_tensors(env_idx, player_idx)
            elif "animal" in tile:
                product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}[tile["animal"]]
                units = int(tile["yield_units"])
                tile["yield_units"] = 0
                inventory[product] = inventory.get(product, 0) + units
                self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "FERTILIZE":
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and self._take_inventory(inventory, "FERTILIZER", 1):
                tile["fertilized_until_day"] = max(tile.get("fertilized_until_day", -1), self.day_idx + 2)
                self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "DIG":
            if tile is not None and not (isinstance(tile, dict) and "animal" in tile):
                if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                    self.plant_tiles[env_idx, player_idx] = torch.maximum(
                        self.plant_tiles[env_idx, player_idx] - 1,
                        torch.tensor(0, dtype=torch.int32, device=self.device),
                    )
                self.tiles[env_idx][player_idx][fy][fx] = None
                self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "FEED":
            if isinstance(tile, dict) and "animal" in tile and not tile.get("fed_today", False):
                if self._take_inventory(inventory, "WHEAT", 1):
                    tile["fed_today"] = True
                    self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "CARE":
            if isinstance(tile, dict) and "animal" in tile and not tile.get("cared_today", False):
                tile["cared_today"] = True
                self._sync_physical_tensors(env_idx, player_idx)
            return
        if op == "COLLECT_FERTILIZER":
            if isinstance(tile, dict) and "animal" in tile and tile.get("fertilizer_available", False):
                tile["fertilizer_available"] = False
                inventory["FERTILIZER"] = inventory.get("FERTILIZER", 0) + 1
                self._sync_physical_tensors(env_idx, player_idx)

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
            order_states = [
                self._parse_market_order(queue[order_idx]) if order_idx < len(queue) else None
                for queue in queues
            ]
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
                        quoted[player_idx] = (op, item, self._cached_market_price(product_idx, self.market_inventory_mirror[env_idx][product_idx]), order_state)
                    elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                        quoted[player_idx] = (op, item, self._cached_market_price(product_idx, self.market_inventory_mirror[env_idx][product_idx] - 1), order_state)
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
        if self.step_idx % self.TOWN_SHOP_SELL_INTERVAL == 0:
            for shop_name in self.town_shops[env_idx]:
                products = self.SHOPS[shop_name]
                multiplier = 2 if len(products) == 1 else 1
                for product in products:
                    self.market_inventory[env_idx, self.PRODUCT_INDEX[product]] -= multiplier
                    self.market_inventory_mirror[env_idx][self.PRODUCT_INDEX[product]] -= multiplier
        if self.step_idx % 24 == 0:
            for product in self.TOWN_CENTER_PRODUCTS:
                self.market_inventory[env_idx, self.PRODUCT_INDEX[product]] -= 1
                self.market_inventory_mirror[env_idx][self.PRODUCT_INDEX[product]] -= 1
        self._refresh_prices(env_idx)
