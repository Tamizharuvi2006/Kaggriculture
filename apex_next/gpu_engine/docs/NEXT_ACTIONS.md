# Next Actions

Current checkpoint:

```text
3H-8K 20-seed full CUDA parity      CLOSED/PASS
3H-8L 100-seed full CUDA parity     NEXT
3H-8M CUDA performance benchmark    BLOCKED
Step 5B PPO                         STOPPED
```

## Next Gate: 3H-8L

Run 100-seed full CUDA parity using cached real action traces.

Acceptance:

```text
seeds tested                  100
real transitions/seed         719
CPU transitions/seed          719
CUDA transitions/seed         719
first_divergence              null
tensor/object divergence      null
terminal divergence           null
unsupported actions           0
actual CUDA used              true
tensor device                 cuda:0
GPU                           NVIDIA GeForce RTX 4050 Laptop GPU
exceptions                    0
```

Rules:

- Reuse cached traces when present.
- Create missing real traces once.
- Do not invoke Step 5B.
- Do not benchmark performance yet.
- Do not modify sealed production artifacts.

Suggested command:

```powershell
C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe apex_next\gpu_engine\step3h8k_multiseed_cuda_parity.py --seed-start 39000 --count 100 --report reports\step3h\cuda\STEP3H8L_100_SEED_CUDA_PARITY.json
```

Expected runtime:

```text
If many traces are missing:  trace creation adds one-time cost
Replay portion:             likely around 20-30 minutes
```

## After 3H-8L Passes

Then run 3H-8M:

```text
CUDA performance benchmark
```

Measure:

```text
games/sec
steps/sec
GPU utilization
CPU utilization
VRAM
RAM
batch size scaling
thermal behavior
```

Only after performance is measured should Step 5B restart with an accelerated
rollout smoke.

## Folder Cleanup Plan

Current safe state:

- Human docs are organized under `apex_next\gpu_engine\docs`.
- Raw JSON evidence stays under `reports`.
- Trace cache stays under `reports\step3h\traces\step3h_real_action_traces`.

Recommended cleanup later:

1. Step 3H report defaults are already updated.
2. Step 3H reports are already migrated.
3. 1-seed CUDA layout verification passed.
4. Leave unrelated research reports alone until their script defaults are audited.
