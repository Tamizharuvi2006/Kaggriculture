# 🛠️ CLOSED_LOOP_CONTROLLER: IMPLEMENTATION SPECIFICATION

> **Module**: `apex_next/research/closed_loop_controller.py`  
> **Interface**: `ClosedLoopController.plan_step(obs, fallback_action)`  
> **Execution Mode**: Observation-Only Dynamic Planning with Critical-Task Hard Invariants

---

## 📋 Key Methods & Capabilities
* `plan_step(obs, fallback_action)`: Primary entry point. Updates farm state, evaluates active task graphs, protects critical milestones, and returns legal action dictionaries.
* `_step_towards(curr, target)`: Manhattan directional path planner with collision avoidance.
* `CRITICAL_TASK_REGISTRY`: Contains 242 validated milestone tasks extracted from champion replays.
