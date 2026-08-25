"""
APEX 4.0 Persistent Regional Worker Coordination Subsystem (RegionManager)
Manages long-lived regional agricultural commitments across farm quadrants.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class RegionState:
    LOCKED = "REGION_LOCKED"
    UNLOCKED = "REGION_UNLOCKED"
    ACTIVATING = "REGION_ACTIVATING"
    ACTIVE = "REGION_ACTIVE"
    SUSTAINING = "REGION_SUSTAINING"
    RELEASED = "REGION_RELEASED"


class Region:
    def __init__(self, region_id, row_range, col_range):
        self.region_id = region_id  # 0: NW (0..4, 0..4), 1: NE (0..4, 5..9), 2: SW (5..9, 0..4), 3: SE (5..9, 5..9)
        self.row_range = row_range
        self.col_range = col_range
        self.state = RegionState.LOCKED
        self.assigned_workers = []
        self.planted_tiles = []
        self.ripe_tiles = []
        self.thirsty_tiles = []
        self.untilled_tiles = []
        self.completed_cycles = 0

    def contains(self, r, c):
        return (self.row_range[0] <= r <= self.row_range[1]) and (self.col_range[0] <= c <= self.col_range[1])

    def update_tiles(self, tiles):
        self.planted_tiles = []
        self.ripe_tiles = []
        self.thirsty_tiles = []
        self.untilled_tiles = []
        
        for t in tiles:
            r = t.get("row", 0)
            c = t.get("col", 0)
            if self.contains(r, c):
                crop = t.get("crop")
                stage = t.get("stage")
                needs_water = t.get("needs_water", False)
                tilled = t.get("tilled", False)
                
                if stage == "RIPE":
                    self.ripe_tiles.append((r, c))
                elif crop is not None and needs_water:
                    self.thirsty_tiles.append((r, c))
                elif crop is not None:
                    self.planted_tiles.append((r, c))
                elif tilled and crop is None:
                    self.untilled_tiles.append((r, c))


class RegionManager:
    """
    Coordinates regional worker leasing and continuous agricultural production.
    """
    def __init__(self):
        self.regions = {
            0: Region(0, (0, 4), (0, 4)),  # NW Quadrant (Base Hub)
            1: Region(1, (0, 4), (5, 9)),  # NE Quadrant
            2: Region(2, (5, 9), (0, 4)),  # SW Quadrant (Target Scaling Region)
            3: Region(3, (5, 9), (5, 9))   # SE Quadrant
        }
        self.worker_leases = {}  # worker_idx -> {region_id, role, lease_start, lease_end, target_tile}

    def update(self, world_model):
        unlocked = world_model.unlocked_quadrants
        for q_id in range(4):
            reg = self.regions[q_id]
            if q_id in unlocked:
                if reg.state == RegionState.LOCKED:
                    reg.state = RegionState.UNLOCKED
            else:
                reg.state = RegionState.LOCKED
            reg.update_tiles(world_model.tiles)
            
        # Update active/sustaining state for SW region
        sw_reg = self.regions[2]
        if sw_reg.state in (RegionState.UNLOCKED, RegionState.ACTIVATING, RegionState.ACTIVE, RegionState.SUSTAINING):
            if len(sw_reg.planted_tiles) > 0 or len(sw_reg.ripe_tiles) > 0 or len(sw_reg.thirsty_tiles) > 0:
                sw_reg.state = RegionState.SUSTAINING
            elif world_model.step >= 152:
                sw_reg.state = RegionState.ACTIVE

    def assign_worker_lease(self, worker_idx, region_id, role="FARMER", start_step=160, duration=560):
        self.worker_leases[worker_idx] = {
            "region_id": region_id,
            "role": role,
            "lease_start": start_step,
            "lease_end": start_step + duration,
            "allowed_tasks": ["WATER", "HARVEST", "PLANT", "TILL", "DROP"],
            "protected_tasks": []
        }
        if worker_idx not in self.regions[region_id].assigned_workers:
            self.regions[region_id].assigned_workers.append(worker_idx)

    def get_assigned_region(self, worker_idx, current_step):
        lease = self.worker_leases.get(worker_idx)
        if lease and lease["lease_start"] <= current_step <= lease["lease_end"]:
            return lease["region_id"]
        return None
