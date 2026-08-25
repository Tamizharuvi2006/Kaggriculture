"""Farm state representation for player's own farm."""
from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from engine.state.observation import Observation, CROPS, ANIMALS

class Tile:
    def __init__(self, x: int, y: int, raw_tile: Any):
        self.x: int = x
        self.y: int = y
        self.pos: Tuple[int, int] = (x, y)
        self.raw = raw_tile
        
        self.is_locked: bool = (raw_tile == "LOCKED")
        self.is_empty: bool = (raw_tile is None)
        self.is_dict: bool = isinstance(raw_tile, dict)
        
        self.kind: Optional[str] = raw_tile.get("kind") if self.is_dict else None
        self.crop: Optional[str] = raw_tile.get("crop") if self.is_dict else None
        self.animal: Optional[str] = raw_tile.get("animal") if self.is_dict else None
        
        self.yield_units: int = int(raw_tile.get("yield_units", 0)) if self.is_dict else 0
        self.watered_today: bool = bool(raw_tile.get("watered_today", False)) if self.is_dict else False
        self.fed_today: bool = bool(raw_tile.get("fed_today", False)) if self.is_dict else False
        self.cared_today: bool = bool(raw_tile.get("cared_today", False)) if self.is_dict else False
        self.fertilizer_available: bool = bool(raw_tile.get("fertilizer_available", False)) if self.is_dict else False
        self.consecutive_unwatered: int = int(raw_tile.get("consecutive_unwatered", 0)) if self.is_dict else 0
        self.consecutive_unfed: int = int(raw_tile.get("consecutive_unfed", 0)) if self.is_dict else 0
        self.planted_day: int = int(raw_tile.get("planted_day", 0)) if self.is_dict else 0

class FarmState:
    """State representation of the player's farm."""
    def __init__(self, obs: Observation):
        self.player_idx = obs.player
        farm_data = obs.farms[self.player_idx] if len(obs.farms) > self.player_idx else {}
        priv_data = obs.private or {}

        self.money: float = float(farm_data.get("money", 0.0) or 0.0)
        self.unlocked_quadrants: List[str] = list(farm_data.get("unlocked_quadrants", ["NW"]) or ["NW"])
        self.hires_today: int = int(farm_data.get("hires_today", 0) or 0)
        
        # Worker positions
        farmer_pos = farm_data.get("farmer", [4, 4]) or [4, 4]
        self.farmer: Tuple[int, int] = (int(farmer_pos[0]), int(farmer_pos[1]))
        self.hands: List[Tuple[int, int]] = [
            (int(h[0]), int(h[1])) for h in (farm_data.get("hands", []) or []) if len(h) >= 2
        ]
        self.all_workers: List[Tuple[int, int]] = [self.farmer] + self.hands
        self.num_workers: int = len(self.all_workers)

        # Private inventories
        self.shed: Dict[str, int] = {k: int(v) for k, v in (priv_data.get("shed", {}) or {}).items()}
        self.seeds: Dict[str, int] = {k: int(v) for k, v in (priv_data.get("seeds", {}) or {}).items()}
        self.carried_inventories: List[Dict[str, int]] = [
            {k: int(v) for k, v in inv.items()}
            for inv in (priv_data.get("inventories", []) or [])
            if isinstance(inv, dict)
        ]
        while len(self.carried_inventories) < self.num_workers:
            self.carried_inventories.append({})

        # Tiles parsing
        self.tiles_grid: List[List[Tile]] = []
        self.tiles_flat: List[Tile] = []
        raw_tiles = farm_data.get("tiles", []) or []
        for y, row in enumerate(raw_tiles):
            row_tiles = []
            for x, raw_tile in enumerate(row):
                t = Tile(x, y, raw_tile)
                row_tiles.append(t)
                self.tiles_flat.append(t)
            self.tiles_grid.append(row_tiles)

        # Categorized tile lookups
        self.plants = [t for t in self.tiles_flat if t.kind == "PLANT" and t.crop]
        self.plants_by_crop: Dict[str, List[Tile]] = {c: [] for c in CROPS}
        for p in self.plants:
            if p.crop in self.plants_by_crop:
                self.plants_by_crop[p.crop].append(p)

        self.animals = [t for t in self.tiles_flat if t.animal in ANIMALS]
        self.animals_by_type: Dict[str, List[Tile]] = {a: [] for a in ANIMALS}
        for a in self.animals:
            if a.animal in self.animals_by_type:
                self.animals_by_type[a.animal].append(a)

        self.pastures_empty = [t for t in self.tiles_flat if t.kind == "PASTURE" and not t.animal]
        self.empty_tiles = [t for t in self.tiles_flat if t.is_empty]
        self.ready_harvests = [t for t in self.plants if t.yield_units > 0]
        self.unwatered_plants = [t for t in self.plants if not t.watered_today]
        self.unfed_animals = [t for t in self.animals if not t.fed_today]

    def total_wheat_inventory(self) -> int:
        return self.shed.get("WHEAT", 0) + sum(inv.get("WHEAT", 0) for inv in self.carried_inventories)

    def total_product_in_shed(self, product: str) -> int:
        return self.shed.get(product, 0)
