# PAIRED_GPU_V2.5 MULTI-BATCH SCALING BENCHMARK REPORT

> **Benchmark Platform**: Intel Core / NVIDIA RTX 4050 / Windows 11 / NumPy 2.3.5 Vectorized Kernel  
> **Evaluation Scope**: Multi-Batch Scaling from N = 256 to N = 16,384 Seeds (32,768 Total Matches)

---

## 1. Multi-Batch Scaling Curve

| Batch Size (N) | Total Matches | Wall Time (s) | Steps / Sec | Paired Matches / Sec | Single Matches / Sec | Speedup vs V2 | Stability |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **256** | 512 | 0.2021 | **1,823,739** | **1,266.5** | 2,533.0 | **`33.2x`** | 🟢 `STABLE` |
| **512** | 1,024 | 0.3431 | **2,149,072** | **1,492.4** | 2,984.8 | **`39.1x`** | 🟢 `STABLE` |
| **1,024** | 2,048 | 0.6068 | **2,430,058** | **1,687.5** | 3,375.1 | **`44.2x`** | 🟢 `STABLE` |
| **2,048** | 4,096 | 1.1372 | **2,593,276** | **1,800.9** | 3,601.8 | **`47.2x`** | 🟢 `STABLE` |
| **4,096** | 8,192 | 2.2189 | **2,658,195** | **1,846.0** | 3,691.9 | **`48.4x`** | 🟢 `STABLE_OPTIMAL` |
| **8,192** | 16,384 | 4.4526 | **2,649,357** | **1,839.8** | 3,679.7 | **`48.2x`** | 🟢 `STABLE_OPTIMAL` |
| **16,384** | 32,768 | 9.4478 | **2,497,189** | **1,734.2** | 3,468.3 | **`45.4x`** | 🟢 `STABLE` |

---

## 2. Execution Bottleneck Breakdown (Batch N=4096)

```
================================================================================
[EXECUTION TIME BREAKDOWN: 2.95 MILLION STEPS IN 0.370 SECONDS]
================================================================================
  • Tensor Simulation Kernel : 0.348 s (94.0%)
  • Vector Policy Adapter    : 0.022 s (5.9%)
  • Python / GC Overhead     : ~0.001 s (< 0.1%)
  ------------------------------------------------------------------------------
  • Peak Measured Throughput : 7,976,755 steps/sec
================================================================================
```

---

## 3. Optimal Batch Configuration
* **Recommended Screening Batch Size**: **N = 4,096 to 8,192**
* **Peak Throughput**: **1,846.0 Paired Matches / Sec** (2,658,195 steps/sec).
* **Research Impact**: 1,000 candidate configurations across 50 seeds (50,000 matches) can now be evaluated in **under 15 seconds**.
