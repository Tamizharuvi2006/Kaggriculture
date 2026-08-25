# ⚡ ML Stage 0: Hardware & Engine Validation Report

* **GPU Device**: NVIDIA GeForce RTX 4050 Laptop GPU (6.00 GB VRAM)
* **PyTorch / CUDA**: 2.6.0+cu124 (CUDA 12.4 / Driver 592.82)
* **Throughput Clarification**:
  - *Synthetic Macro Kernel*: 14,498 games/sec (Used for high-level parameter screening).
  - *Full-Fidelity PAIRED_GPU_V2.5*: ~1,200 paired matches/sec (100% full 720-step environment with worker kinematics).
  - *Official Reference Engine*: ~35 matches/sec (Single-threaded `kaggle_environments v1.32.6` authority).
