# 📋 TODO.md — Next Engineering Task

## 🔬 Research 13: Task Scheduler & Work Generator Audit

### Objective
Examine the V18 centralized action generator `_assign_actions()` and `_market_orders()` to determine why **3.33 workers are idle every step** and **10 unlocked tiles sit unplanted**, despite having **$28.7k in cash liquidity**.

### Key Questions to Answer
1. Why does `_assign_actions()` fail to assign tasks to idle workers when free farmland exists?
2. Which profitable task types (e.g. crop planting, weeding, crop watering, market sales) are currently blocked or missing?
3. How can we replace static task queues with a dynamic, ROI-based task generator?

### Constraints
- Keep `baseline/submission_v81.py` frozen.
- Perform all experiments inside `experiments/`.
