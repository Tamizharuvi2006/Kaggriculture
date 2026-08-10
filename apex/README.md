# 🏛️ L+ APEX — Autonomous Kaggriculture Discovery Engine

> See master documentation at [README.md](file:///D:/kagriulture/Kaggriculture/README.md) and detailed experiment logs at [APEX_EXPERIMENT_HISTORY.md](file:///D:/kagriulture/Kaggriculture/docs/APEX_EXPERIMENT_HISTORY.md).

### Core Components
- `world_model.py`: Compact state representation & observation normalization.
- `expert.py`: L+ 4.1 frozen expert baseline wrapper.
- `planner.py`: Action variation & candidate generator.
- `action_safety.py`: Deterministic financial & operational constraint filters.
- `marginal_evaluator.py`: Marginal Counterfactual Value (MCV) calculator.
- `counterfactual.py`: Counterfactual simulation & UCB exploration eligibility.
- `divergence_controller.py`: Single-deviation selection & curriculum enforcement.
- `policy.py`: Full APEX runtime decision orchestrator with shadow validation.
- `experience_memory.py`: Telemetry, calibration database & error tracking.
- `agent.py`: Kaggle environment entrypoint (`agent(obs, conf)`).
