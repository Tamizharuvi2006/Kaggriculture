# Step 3H Evidence Index

This index lists the evidence files that matter for the current GPU/CUDA
simulator work.

## Current Best Reports

### CPU/vector parity

```text
D:\Kaggriculture\reports\step3h\vector\STEP3H7D_OPTIMIZED_100_SEED_PARITY.json
```

Meaning:

- Corrected vector CPU engine passed 100-seed full parity.

```text
D:\Kaggriculture\reports\step3h\vector\STEP3H7D_OPTIMIZED_PERFORMANCE_100.json
```

Meaning:

- Corrected vector CPU engine performance baseline.
- Baseline recorded as about 13.76 games/sec.

### CUDA semantic slice gates

```text
D:\Kaggriculture\reports\step3h\cuda\STEP3H8B_PHYSICAL_TENSOR_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8C_PHYSICAL_SLICE_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8D_CROP_ACTION_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8E_ANIMAL_ACTION_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8F_CROP_LIFECYCLE_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8G_ANIMAL_LIFECYCLE_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8H_FULL_STEP_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8I_TERMINAL_REWARD_AUDIT.json
```

Meaning:

- CUDA physical tensors, actions, lifecycle, full step ownership, and terminal
  semantics all passed their scoped gates.

### Full CUDA trajectory

```text
D:\Kaggriculture\reports\step3h\cuda\STEP3H8J_FULL_CUDA_TRAJECTORY_AUDIT.json
D:\Kaggriculture\reports\step3h\cuda\STEP3H8J_FULL_CUDA_TRAJECTORY_AUDIT_POST_DEFERRED_SYNC.json
```

Meaning:

- Full 719-transition seed 39000 trajectory passed.
- Post-deferred-sync audit confirms the optimization did not break 8J.

### Multi-seed CUDA parity

```text
D:\Kaggriculture\reports\step3h\cuda\STEP3H8K_20_SEED_CUDA_PARITY.json
```

Meaning:

- 20/20 full CUDA trajectories passed.
- All seeds had 719 real/CPU/CUDA transitions.
- No first divergence.
- No tensor/object divergence.
- No terminal divergence.
- No unsupported actions.
- CUDA actually used on `cuda:0`.

### Hot-path profiles

```text
D:\Kaggriculture\reports\step3h\profiles\STEP3H8K_HOTPATH_PROFILE_2SEED_24STEP.json
D:\Kaggriculture\reports\step3h\profiles\STEP3H8K_HOTPATH_PROFILE_2SEED_24STEP_DEFERRED_SYNC.json
```

Meaning:

- Before deferred sync, `gpu_step_integrated` dominated runtime.
- After deferred sync, 24-step/2-seed profile improved from 6.717 sec to
  0.895 sec in `gpu_step_integrated`.

### Real action traces

```text
D:\Kaggriculture\reports\step3h\traces\step3h_real_action_traces\
```

Current important traces:

```text
real_action_trace_seed_39000_steps_720.json
...
real_action_trace_seed_39019_steps_720.json
```

These are truth-derived action traces from real Kaggriculture. They should be
kept and reused for future CPU/CUDA replay audits.

## Evidence Rules

- Do not delete trace files.
- Do not overwrite reports silently when a new gate has different semantics.
- Use new report names for probes and post-optimization reruns.
- Do not mark a gate closed from a CPU fallback.
- Always record CUDA availability, GPU name, tensor device, and
  `actual_cuda_used`.
