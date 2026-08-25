"""Track B: High-Throughput Unit Action Dispatcher.
Dynamically coordinates worker units across custom spatial zoning:
- Directs workers to animal care / milking daily
- Directs workers to crop watering & harvesting
- Optimizes movement paths to minimize transit steps
"""
from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from engine.state.farm_state import FarmState, Tile

SHED_POS = (4, 4)

def get_manhattan_dist(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def get_step_towards(curr: Tuple[int, int], target: Tuple[int, int]) -> str:
    """Returns optimal single-step compass direction towards target."""
    cx, cy = curr
    tx, ty = target
    if tx > cx:
        return "E"
    elif tx < cx:
        return "W"
    elif ty > cy:
        return "S"
    elif ty < cy:
        return "N"
    return "PASS"

class UnitDispatcher:
    """Assigns priority actions and movements to all farmer & hand units."""

    @staticmethod
    def dispatch_all(farm: FarmState) -> Tuple[List[str], List[List[str]]]:
        num_workers = farm.num_workers
        worker_positions = farm.all_workers
        unit_actions: List[List[str]] = [["PASS"] for _ in range(num_workers)]

        assigned_targets: set[Tuple[int, int]] = set()

        # Build task queues
        ready_harvests = list(farm.ready_harvests)
        unwatered_crops = list(farm.unwatered_plants)
        unmilked_animals = [a for a in farm.animals if not a.cared_today]
        unfed_animals = list(farm.unfed_animals)

        for w_idx in range(num_workers):
            w_pos = worker_positions[w_idx]
            curr_tile = farm.tiles_grid[w_pos[1]][w_pos[0]] if (0 <= w_pos[1] < len(farm.tiles_grid) and 0 <= w_pos[0] < len(farm.tiles_grid[0])) else None

            # 1. Action on Current Tile
            if curr_tile:
                # Harvest ready crop
                if curr_tile.kind == "PLANT" and curr_tile.yield_units > 0:
                    unit_actions[w_idx] = ["HARVEST"]
                    continue
                # Milk/Care animal
                if curr_tile.animal and not curr_tile.cared_today:
                    unit_actions[w_idx] = ["CARE"]
                    continue
                # Water crop
                if curr_tile.kind == "PLANT" and not curr_tile.watered_today:
                    unit_actions[w_idx] = ["WATER"]
                    continue
                # Collect fertilizer
                if curr_tile.animal and curr_tile.fertilizer_available:
                    unit_actions[w_idx] = ["COLLECT_FERTILIZER"]
                    continue

            # 2. Find Nearest Unassigned Target
            best_target: Optional[Tuple[int, int]] = None
            best_dist = 999

            # Priority A: Unmilked animals
            for a in unmilked_animals:
                if a.pos not in assigned_targets:
                    d = get_manhattan_dist(w_pos, a.pos)
                    if d < best_dist:
                        best_dist = d
                        best_target = a.pos

            # Priority B: Ready harvests
            if not best_target:
                for h in ready_harvests:
                    if h.pos not in assigned_targets:
                        d = get_manhattan_dist(w_pos, h.pos)
                        if d < best_dist:
                            best_dist = d
                            best_target = h.pos

            # Priority C: Unwatered crops
            if not best_target:
                for u in unwatered_crops:
                    if u.pos not in assigned_targets:
                        d = get_manhattan_dist(w_pos, u.pos)
                        if d < best_dist:
                            best_dist = d
                            best_target = u.pos

            # Move towards target
            if best_target:
                assigned_targets.add(best_target)
                direction = get_step_towards(w_pos, best_target)
                if direction != "PASS":
                    unit_actions[w_idx] = ["MOVE", direction]
                else:
                    unit_actions[w_idx] = ["PASS"]
            else:
                unit_actions[w_idx] = ["PASS"]

        farmer_act = unit_actions[0] if unit_actions else ["PASS"]
        hands_act = unit_actions[1:] if len(unit_actions) > 1 else []
        return farmer_act, hands_act
