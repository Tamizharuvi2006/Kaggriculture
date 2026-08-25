"""Task scheduling and labor dispatch for all farm units."""
from __future__ import annotations
from typing import List, Dict, Tuple, Any, Optional, Set
from engine.state.observation import Observation, CROPS, ANIMALS
from engine.state.farm_state import FarmState
from engine.execution.farmer import move_toward, manhattan_dist, shed_access_tiles

class LaborScheduler:
    """Assigns optimal physical actions to all available workers each step."""

    @staticmethod
    def assign_worker_actions(
        obs: Observation,
        farm: FarmState,
        target_crop_plan: Dict[Tuple[int, int], str],
        target_animal_plan: Dict[Tuple[int, int], str],
    ) -> List[List[str]]:
        num_workers = farm.num_workers
        actions: List[List[str]] = [["PASS"] for _ in range(num_workers)]
        free_workers: Set[int] = set(range(num_workers))
        access_tiles = shed_access_tiles(10)

        # -------------------------------------------------------------
        # 1. EXISTENTIAL TASK: Feed unfed animals
        # -------------------------------------------------------------
        if obs.day < 29:
            unfed_positions = [t.pos for t in farm.unfed_animals]
            for pos in unfed_positions:
                if not free_workers:
                    break
                # Find worker carrying wheat or best available worker
                wheat_carriers = [
                    idx for idx in free_workers
                    if farm.carried_inventories[idx].get("WHEAT", 0) > 0
                ]
                if wheat_carriers:
                    best_worker = min(wheat_carriers, key=lambda idx: manhattan_dist(farm.all_workers[idx], pos))
                    worker_pos = farm.all_workers[best_worker]
                    if worker_pos == pos:
                        actions[best_worker] = ["FEED"]
                    else:
                        actions[best_worker] = move_toward(worker_pos, pos)
                    free_workers.remove(best_worker)

        # -------------------------------------------------------------
        # 2. ANIMAL PLACEMENT: Place purchased animals in pastures
        # -------------------------------------------------------------
        for idx in list(free_workers):
            inv = farm.carried_inventories[idx]
            for animal in ANIMALS:
                if inv.get(animal, 0) > 0:
                    empty_pastures = [
                        t.pos for t in farm.pastures_empty
                        if target_animal_plan.get(t.pos) == animal
                    ]
                    if empty_pastures:
                        target = min(empty_pastures, key=lambda p: manhattan_dist(farm.all_workers[idx], p))
                        if farm.all_workers[idx] == target:
                            actions[idx] = ["PLACE", animal]
                        else:
                            actions[idx] = move_toward(farm.all_workers[idx], target)
                        free_workers.remove(idx)
                        break

        # -------------------------------------------------------------
        # 3. HARVEST READY CROPS: High-value cash realization
        # -------------------------------------------------------------
        ready_positions = [t.pos for t in farm.ready_harvests]
        for pos in ready_positions:
            if not free_workers:
                break
            best_worker = min(free_workers, key=lambda idx: manhattan_dist(farm.all_workers[idx], pos))
            worker_pos = farm.all_workers[best_worker]
            if worker_pos == pos:
                actions[best_worker] = ["HARVEST"]
            else:
                actions[best_worker] = move_toward(worker_pos, pos)
            free_workers.remove(best_worker)

        # -------------------------------------------------------------
        # 4. WATER CROPS: Water all unwatered crops (critical cadence)
        # -------------------------------------------------------------
        unwatered_positions = [t.pos for t in farm.unwatered_plants]
        for pos in unwatered_positions:
            if not free_workers:
                break
            best_worker = min(free_workers, key=lambda idx: manhattan_dist(farm.all_workers[idx], pos))
            worker_pos = farm.all_workers[best_worker]
            if worker_pos == pos:
                actions[best_worker] = ["WATER"]
            else:
                actions[best_worker] = move_toward(worker_pos, pos)
            free_workers.remove(best_worker)

        # -------------------------------------------------------------
        # 5. PLANT & TILL: Expand target crop plan
        # -------------------------------------------------------------
        for pos, desired_crop in target_crop_plan.items():
            if not free_workers:
                break
            x, y = pos
            if not (0 <= y < len(farm.tiles_grid) and 0 <= x < len(farm.tiles_grid[0])):
                continue
            tile = farm.tiles_grid[y][x]
            if tile.is_locked or tile.kind == "PASTURE" or (tile.kind == "PLANT" and tile.crop == desired_crop):
                continue
            
            # Tile needs prep / planting
            best_worker = min(free_workers, key=lambda idx: manhattan_dist(farm.all_workers[idx], pos))
            worker_pos = farm.all_workers[best_worker]
            
            if tile.kind == "WEED":
                if worker_pos == pos: actions[best_worker] = ["CLEAR_WEED"]
                else: actions[best_worker] = move_toward(worker_pos, pos)
                free_workers.remove(best_worker)
            elif tile.is_empty:
                if worker_pos == pos: actions[best_worker] = ["TILL"]
                else: actions[best_worker] = move_toward(worker_pos, pos)
                free_workers.remove(best_worker)
            elif tile.kind == "TILLED" and farm.seeds.get(desired_crop, 0) > 0:
                if worker_pos == pos: actions[best_worker] = ["PLANT", desired_crop]
                else: actions[best_worker] = move_toward(worker_pos, pos)
                free_workers.remove(best_worker)

        # -------------------------------------------------------------
        # 6. RETURN / SHED DROP FOR REMAINING WORKERS
        # -------------------------------------------------------------
        for idx in list(free_workers):
            inv = farm.carried_inventories[idx]
            worker_pos = farm.all_workers[idx]
            total_items = sum(inv.values())
            
            # If carrying harvest load at dusk or when full, return to shed
            if (obs.hour >= 20 and total_items > 0) or total_items >= 25:
                nearest_access = min(access_tiles, key=lambda p: manhattan_dist(worker_pos, p))
                if worker_pos in access_tiles:
                    actions[idx] = ["DROP"]
                else:
                    actions[idx] = move_toward(worker_pos, nearest_access)
            else:
                actions[idx] = ["PASS"]

        return actions
