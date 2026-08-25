"""
APEX 4.0 Semantic Task Graph & Dependency Engine
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class Task:
    def __init__(self, task_id, task_type, target_pos=None, priority=100.0, prerequisites=None, deadline=None, payload=None):
        self.task_id = task_id
        self.task_type = task_type
        self.target_pos = target_pos
        self.priority = priority
        self.prerequisites = prerequisites or []
        self.deadline = deadline
        self.payload = payload or {}
        self.assigned_worker = None
        self.completed = False


class APEX4TaskGraph:
    """
    Evaluates active goals and builds dependency-aware task queues on each step.
    """
    def __init__(self):
        self.active_tasks = []
        self.critical_milestones = {
            1: {"type": "BUILD_PASTURE", "worker_indices": [0], "priority": 1000.0},
            159: {"type": "BUILD_PASTURE", "worker_indices": [2, 3], "priority": 1000.0},
            3: {"type": "PICKUP", "item": "COW", "worker_indices": [0], "priority": 900.0},
            7: {"type": "PICKUP", "item": "COW", "worker_indices": [0], "priority": 900.0},
            8: {"type": "PICKUP", "item": "SHEEP", "worker_indices": [0], "priority": 900.0},
            170: {"type": "PICKUP", "item": "COW", "worker_indices": [0], "priority": 900.0}
        }

    def evaluate_tasks(self, world_model):
        tasks = []
        step = world_model.step
        hour = world_model.hour
        
        # 1. Critical Infrastructure Milestones
        if step in self.critical_milestones:
            m = self.critical_milestones[step]
            tasks.append(Task(
                task_id=f"CRITICAL_{step}",
                task_type=m["type"],
                priority=m["priority"],
                payload={"worker_indices": m.get("worker_indices", [])}
            ))

        # 2. Dynamic Agriculture Tasks
        for tile in world_model.tiles:
            r = tile.get("row", 0)
            c = tile.get("col", 0)
            crop = tile.get("crop")
            stage = tile.get("stage")
            needs_water = tile.get("needs_water", False)
            tilled = tile.get("tilled", False)
            
            if stage == "RIPE":
                tasks.append(Task(f"HARVEST_{r}_{c}", "HARVEST", target_pos=(r, c), priority=350.0))
            elif crop is not None and needs_water:
                tasks.append(Task(f"WATER_{r}_{c}", "WATER", target_pos=(r, c), priority=250.0))
            elif crop is None and tilled and world_model.get_shed_item("STRAWBERRY_SEED") > 0:
                tasks.append(Task(f"PLANT_{r}_{c}", "PLANT", target_pos=(r, c), priority=200.0, payload={"crop": "STRAWBERRY"}))

        # 3. Dynamic Logistics Tasks (Hour 22 Shed Drop)
        if hour == 22:
            tasks.append(Task("HOUR22_SHED_DROP", "DROP", target_pos=(3, 3), priority=300.0))

        self.active_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        return self.active_tasks
