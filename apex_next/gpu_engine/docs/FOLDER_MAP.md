# GPU Engine Folder Map

This map is the quick answer to: "what is where?"

## Main Code Areas

```text
D:\Kaggriculture\apex_next\gpu_engine\
```

General GPU/simulator work folder. It contains old screeners, parity audits,
profilers, and Step 3H validation scripts.

Important current files:

```text
paired_sim_v2.py
    Exact replay/reference simulator used to discover semantics.

step3h_parity_audit.py
    Early real Kaggriculture vs PairedSimV2 parity harness.

step3h_multiseed_parity.py
    Multi-seed CPU/reference parity harness.

step3h_performance_benchmark.py
    Diagnostic benchmark for the exact replay path.

step3h7_vector_port_audit.py
    Corrected vector-port parity audit.

step3h7_vector_performance.py
    Corrected vector-engine performance checks.

step3h8_cuda_port_audit.py
    CUDA foundation audit.

step3h8b_physical_tensor_audit.py
    CUDA physical tensor mirror audit.

step3h8c_physical_slice_audit.py
    CUDA movement/carrying/build/place audit.

step3h8d_crop_action_audit.py
    CUDA crop action audit.

step3h8e_animal_action_audit.py
    CUDA animal action audit.

step3h8f_crop_lifecycle_audit.py
    CUDA daily crop lifecycle audit.

step3h8g_animal_lifecycle_audit.py
    CUDA daily animal lifecycle audit.

step3h8h_full_step_audit.py
    Integrated CUDA step ownership audit.

step3h8i_terminal_reward_audit.py
    Terminal and reward semantics audit.

step3h8j_full_cuda_trajectory_audit.py
    Full single-seed CUDA trajectory parity audit.

step3h8k_multiseed_cuda_parity.py
    Full multi-seed CUDA trajectory parity audit.

profile_step3h8k_replay_hotpath.py
    Short profiler for the 8K cached-trace replay hot path.
```

## Current Engine Implementations

```text
D:\Kaggriculture\apex_next\gpu_engine\paired_gpu_v25\
```

Important files:

```text
corrected_vector_engine.py
    Parity-correct CPU/vector engine.

corrected_cuda_engine.py
    Parity-correct CUDA engine under validation.

paired_engine_v25.py
    Older fast V25 engine. Useful as speed reference only; not current truth.
```

## Human-Readable Documentation

```text
D:\Kaggriculture\apex_next\gpu_engine\docs\
```

This folder is newly added as the canonical place for human-readable Step 3H
status and organization docs.

Files:

```text
README.md
STEP3H_GPU_CUDA_PROGRESS_REPORT.md
FOLDER_MAP.md
EVIDENCE_INDEX.md
NEXT_ACTIONS.md
```

## Raw Reports And Evidence

```text
D:\Kaggriculture\reports\
```

This folder is messy because it stores reports from many research phases, not
only Step 3H. Do not delete or move files here blindly.

Current Step 3H report pattern:

```text
STEP3H*.json
STEP3H7*.json
STEP3H8*.json
```

Trace cache:

```text
D:\Kaggriculture\reports\step3h\traces\step3h_real_action_traces\
```

Purpose:

- Stores deterministic real Kaggriculture action traces.
- Lets CPU/CUDA parity audits replay the same truth-derived actions without
  regenerating real environment episodes every time.

## Current Step 3H Report Layout

The Step 3H reports have been moved into:

```text
D:\Kaggriculture\reports\step3h\
    parity\
    vector\
    cuda\
    profiles\
    traces\
    seed_reports\
```

Migration status:

1. Step 3H reports moved into the folders above.
2. Step 3H script defaults updated.
3. Trace loading keeps old-path fallback.
4. 1-seed CUDA layout verification passed.
5. Unrelated research reports remain untouched.
