"""Probabilistic opponent model with uncertainty bounds and footprint tracking."""
from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from engine.state.observation import Observation, CROPS, ANIMALS, PRODUCTS

class ProbabilisticInventory:
    """Probabilistic representation of hidden opponent inventory with uncertainty."""
    def __init__(
        self,
        estimate: float = 0.0,
        lower: float = 0.0,
        upper: float = 0.0,
        uncertainty: float = 0.0,
        floor_risk: float = 0.0,
        dump_probability: float = 0.0,
    ):
        self.estimate: float = float(estimate)
        self.lower: float = float(lower)
        self.upper: float = float(upper)
        self.uncertainty: float = float(uncertainty)
        self.floor_risk: float = float(floor_risk)  # Probability that opponent dumping crashes price to floor
        self.dump_probability: float = float(dump_probability)

    def to_dict(self) -> Dict[str, float]:
        return {
            "estimate": round(self.estimate, 1),
            "lower": round(self.lower, 1),
            "upper": round(self.upper, 1),
            "uncertainty": round(self.uncertainty, 1),
            "floor_risk": round(self.floor_risk, 3),
            "dump_probability": round(self.dump_probability, 3),
        }

class OpponentState:
    """Probabilistic state of the opponent's farm and commodity pipelines."""
    def __init__(self, obs: Observation, prev_state: Optional[OpponentState] = None):
        self.player_idx = obs.opp_player
        opp_data = obs.farms[self.player_idx] if len(obs.farms) > self.player_idx else {}
        
        self.money: float = float(opp_data.get("money", 0.0) or 0.0)
        self.unlocked_quadrants: List[str] = list(opp_data.get("unlocked_quadrants", ["NW"]) or ["NW"])
        
        # Worker positions
        farmer_pos = opp_data.get("farmer", [4, 4]) or [4, 4]
        self.farmer: Tuple[int, int] = (int(farmer_pos[0]), int(farmer_pos[1]))
        self.hands: List[Tuple[int, int]] = [
            (int(h[0]), int(h[1])) for h in (opp_data.get("hands", []) or []) if len(h) >= 2
        ]
        self.num_workers: int = 1 + len(self.hands)

        # Visible tiles analysis
        raw_tiles = opp_data.get("tiles", []) or []
        self.plants_by_crop: Dict[str, int] = {c: 0 for c in CROPS}
        self.animals_by_type: Dict[str, int] = {a: 0 for a in ANIMALS}
        self.ready_harvests: Dict[str, int] = {c: 0 for c in CROPS}
        
        for row in raw_tiles:
            for tile in row:
                if isinstance(tile, dict):
                    crop = tile.get("crop")
                    if crop in self.plants_by_crop:
                        self.plants_by_crop[crop] += 1
                        if int(tile.get("yield_units", 0)) > 0:
                            self.ready_harvests[crop] += int(tile.get("yield_units", 0))
                    animal = tile.get("animal")
                    if animal in self.animals_by_type:
                        self.animals_by_type[animal] += 1

        self.total_plants = sum(self.plants_by_crop.values())
        self.total_animals = sum(self.animals_by_type.values())

        # Probabilistic inventory estimation
        self.inventory: Dict[str, ProbabilisticInventory] = {}
        for p in PRODUCTS:
            self.inventory[p] = self._estimate_product_inventory(obs, p, prev_state)

        # Meta profile classification
        self.is_carrot_rusher: bool = (self.plants_by_crop.get("CARROT", 0) >= 6)
        self.is_livestock_heavy: bool = (self.animals_by_type.get("COW", 0) + self.animals_by_type.get("SHEEP", 0) >= 6)
        self.is_strawberry_heavy: bool = (self.plants_by_crop.get("STRAWBERRY", 0) >= 12)
        self.has_zero_tomatoes: bool = (self.plants_by_crop.get("TOMATO", 0) == 0)

    def _estimate_product_inventory(
        self,
        obs: Observation,
        product: str,
        prev_state: Optional[OpponentState] = None
    ) -> ProbabilisticInventory:
        """Constructs probabilistic inventory intervals based on visible production capacity."""
        if product in CROPS:
            num_plants = self.plants_by_crop.get(product, 0)
            ready_qty = self.ready_harvests.get(product, 0)
            cfg = CROPS[product]
            yield_multiplier = float(cfg["max_yield"])
            
            # Base estimate from ready harvests + carried estimates
            lower = float(ready_qty)
            estimate = lower + float(num_plants * 0.5 * yield_multiplier)
            upper = lower + float(num_plants * yield_multiplier * 2.0)
            uncertainty = max(5.0, upper - lower)
            
            # Floor risk: risk that opponent dump causes price collapse
            # If opponent has > 10 active plants of this crop, floor risk is very high
            floor_risk = min(1.0, float(num_plants) / 10.0) if num_plants > 0 else 0.0
            dump_prob = 0.85 if ready_qty >= 4 else (0.40 if num_plants > 0 else 0.05)
            
            return ProbabilisticInventory(
                estimate=estimate,
                lower=lower,
                upper=upper,
                uncertainty=uncertainty,
                floor_risk=floor_risk,
                dump_probability=dump_prob
            )
        elif product in ("MILK", "WOOL"):
            animal = "COW" if product == "MILK" else "SHEEP"
            num_animals = self.animals_by_type.get(animal, 0)
            lower = 0.0
            estimate = float(num_animals * 2.0)
            upper = float(num_animals * 6.0)
            uncertainty = max(2.0, upper - lower)
            floor_risk = min(1.0, float(num_animals) / 8.0)
            dump_prob = 0.90 if num_animals >= 4 else 0.30
            return ProbabilisticInventory(
                estimate=estimate,
                lower=lower,
                upper=upper,
                uncertainty=uncertainty,
                floor_risk=floor_risk,
                dump_probability=dump_prob
            )
        else:
            return ProbabilisticInventory(estimate=0.0, lower=0.0, upper=10.0, uncertainty=10.0, floor_risk=0.0, dump_probability=0.1)
