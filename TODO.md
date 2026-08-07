# 📋 TODO.md — Next Engineering Task

## 🔬 Research 16: ROI-Based Task Dispatcher & Labor Optimizer

### Objective
Replace V18's static task queue matching with an explicit **ROI-Ranked Task Dispatcher** that prioritizes high-value tasks (**Strawberries: $73.63/turn**, **Cows: $28.86/turn**) over low-ROI tasks, and optimizes worker transit positioning.

### Empirical Insights from Research 15
- **Strawberry Harvesting/Planting**: **$73.63 / worker-turn** (Rank 1)
- **Melon Harvesting/Planting**: **$40.53 / worker-turn** (Rank 2)
- **Cow Care & Milking**: **$28.86 / worker-turn** (Rank 3)
- **Wheat Planting**: **$13.51 / worker-turn** (Rank 4)
- **Idle / Walking**: **76.65% of all worker-turns** (48.66% Transit + 27.99% Idle)
- **Theoretical Max Score Potential**: **$307,569.23**

### Execution Plan
1. Create `experiments/research16_roi_dispatcher.py`.
2. Keep `baseline/submission_v81.py` frozen.
3. Test dynamic task priority scoring where Strawberry & Cow tasks preempt low-margin tasks and reduce transit distance traps.
