"""Pathing and spatial navigation for farm workers."""
from __future__ import annotations
from typing import Tuple, List, Optional, Dict, Any

def manhattan_dist(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def shed_access_tiles(board_size: int = 10) -> List[Tuple[int, int]]:
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]

def move_toward(current: Tuple[int, int], target: Tuple[int, int]) -> List[str]:
    """Generates the optimal 1-step move toward target coordinate."""
    cx, cy = current
    tx, ty = target
    
    if cx == tx and cy == ty:
        return ["PASS"]
    
    dx = tx - cx
    dy = ty - cy
    
    # Move along axis with larger distance first
    if abs(dx) >= abs(dy):
        if dx > 0: return ["EAST"]
        elif dx < 0: return ["WEST"]
    else:
        if dy > 0: return ["SOUTH"]
        elif dy < 0: return ["NORTH"]
        
    if dx > 0: return ["EAST"]
    elif dx < 0: return ["WEST"]
    elif dy > 0: return ["SOUTH"]
    elif dy < 0: return ["NORTH"]
    
    return ["PASS"]

class FarmerExecutor:
    """Navigation and basic action resolver."""
    @staticmethod
    def navigate(current_pos: Tuple[int, int], target_pos: Tuple[int, int]) -> List[str]:
        return move_toward(current_pos, target_pos)
