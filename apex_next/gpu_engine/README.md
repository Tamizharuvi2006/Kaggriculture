# ⚡ APEX Fast Research Engine v1 (Python Reference + CUDA Batch Architecture)

> **Hardware Target**: NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM, 2,560 CUDA Cores) + Multi-Core CPU  
> **Core Role**: High-throughput strategy space search & candidate screening machine (NOT the final judge).

## Current Step 3H Status

The current CUDA parity work is documented in:

`D:\Kaggriculture\apex_next\gpu_engine\docs\README.md`

Start there before changing simulator, CUDA, PPO, or benchmark code. The latest
closed gate is:

```text
3H-8K 20-seed full CUDA trajectory parity: PASS
```

Next gate:

```text
3H-8L 100-seed full CUDA trajectory parity
```

Do not start Step 5B PPO or CUDA performance benchmarking until 3H-8L closes.

---

## 🏛️ Simulation Hierarchy: The Parity Wall

```
              🧠 RESEARCH SEARCH SPACE
                         │
                         ▼
             ⚡ FAST GPU/VECTOR ENGINE
           (Thousands of Screening Runs)
                         │
                         ▼
                 🏆 TOP CANDIDATES
                         │
                         ▼
             🔬 DIFFERENTIAL VALIDATION
            (Fast Engine == Pinned Ref?)
                    │          │
                   FAIL       PASS
                    │          │
                    ▼          ▼
             ❌ DISCARD   🛡️ OFFICIAL TEST
                         (N ≥ 100 Frozen)
                               │
                               ▼
                         📊 6-GATE JUDGE
                               │
                               ▼
                         🚀 ONE SUBMISSION
```

---

## 🛡️ Non-Negotiable Contract & Pinned Provenance

1. **Untrusted Accelerator Rule**:
   > *"The accelerated engine is untrusted for promotion until it passes differential validation against the pinned reference environment/version."*
2. **Pinned Environment Authority**:
   - Pinned Package: `kaggle_environments`
   - Episode Steps: `720` (24 steps/day)
   - Configuration Parameters: `townCenterSellInterval = 24`, `seed` deterministic
   - The environment version and its configuration hash are permanently recorded in the experiment provenance ledger.
3. **Role Separation**:
   - **GPU Engine**: Strategy space explorer & candidate filter (ranking top 50–100 promising parameter regions).
   - **Official Engine + 6-Gate Judge**: Final arbiter for all Kaggle production cutovers.

---

## 🎯 4-Stage Fast Engine Roadmap

| Stage | Focus | Milestone / Verification Gate |
| :--- | :--- | :--- |
| **Stage 1: Fidelity** | Reference Equivalence | Golden trajectory comparison between fast simulator and pinned `kaggle_environments` on identical seeds. Zero deviation allowed. |
| **Stage 2: Benchmark** | Progressive Scaling | Hardware profile on RTX 4050: benchmark $32 \rightarrow 64 \rightarrow 128 \rightarrow 256 \rightarrow 512$ environments; measure games/sec, VRAM, and GPU/CPU utilization to find optimal throughput. |
| **Stage 3: Mass Screening** | Broad Search | Run 1,000 to 10,000+ candidate parameter sweeps (pricing thresholds, liquidity floors, animal ratios) to isolate high-performing strategy clusters. |
| **Stage 4: Safety** | Official Validation | Candidate winners from Stage 3 enter the formal differential check $\rightarrow$ frozen 100-seed holdout $\rightarrow$ 6-dimension statistical gate $\rightarrow$ single release. |

---

## 📁 Engine Modules

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Python Fast Reference** | [`python_ref_engine.py`](file:///D:/kaggriculture/apex_next/gpu_engine/python_ref_engine.py) | In-memory reference simulator with zero process-spawn overhead. |
| **Differential Tester** | [`differential_tester.py`](file:///D:/kaggriculture/apex_next/gpu_engine/differential_tester.py) | Golden trajectory validator against the pinned `kaggle_environments` reference. |
| **CUDA Batch Engine** | [`cuda_batch_engine.py`](file:///D:/kaggriculture/apex_next/gpu_engine/cuda_batch_engine.py) | Vectorized multi-environment parallel simulator ($B$ parallel games). |
| **Throughput Benchmark** | [`benchmark_throughput.py`](file:///D:/kaggriculture/apex_next/gpu_engine/benchmark_throughput.py) | Progressive scaling benchmark tracking throughput and resource utilization. |
