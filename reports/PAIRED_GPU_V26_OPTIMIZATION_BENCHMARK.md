# ⚡ PAIRED_GPU_V2.5 OPTIMIZED MULTI-BATCH BENCHMARK REPORT

> **Benchmark Platform**: Intel Core / NVIDIA GeForce RTX 4050 Laptop / Windows 11  
> **Engine State**: `PAIRED_GPU_V2.5 (Optimized Contiguous Block Slice)`  
> **Evaluation Scope**: Scaling from $N = 256$ to $N = 16{,}384$ Seeds ($32{,}768$ Matches)

---

## 📊 1. Multi-Batch Scaling Curve Comparison

| Batch Size ($N$) | Total Matches | Pre-Opt Wall Time (s) | Optimized Wall Time (s) | Optimized Steps / Sec | Optimized Paired Matches/s | Total Speedup vs Initial V2 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **256** | 512 | 1.1188 s | **0.4442 s** | **829,830** | **576.3** | **`~26x`** |
| **512** | 1,024 | 2.0874 s | **0.7955 s** | **926,806** | **643.6** | **`~29x`** |
| **1,024** | 2,048 | 4.4057 s | **1.5049 s** | **979,844** | **680.4** | **`~31x`** |
| **2,048** | 4,096 | 8.8997 s | **2.7330 s** | **1,079,059** | **749.3** | **`~34x`** |
| **4,096** | 8,192 | 17.6113 s | **5.0520 s** | **1,167,508** | **810.8** | **`~36x`** |
| **8,192** | 16,384 | 35.2420 s | **10.3754 s** | **1,136,969** | **789.6** | **`~35x`** |
| **16,384** | 32,768 | 71.5136 s | **21.7777 s** | **1,083,354** | **752.3** | **`~34x`** |

---

## 🔬 2. Throughput & Latency Highlights
* **Peak End-to-End Throughput**: **`1,167,508 steps/sec` (810.8 Paired Matches / Sec)** at $N=4{,}096$.
* **Peak Hot Step Loop Throughput**: **`3,382,251 steps/sec` (2.95M steps in 0.87 seconds)**.
* **50-Seed Validation**: Evaluated in **`0.25 seconds`** (vs 3.33 seconds in initial V2).
* **Parity Certification**: **`100.0% Trajectory Parity ($0.01 Delta, 0.00% WR Delta)`**.

---

## 🏆 3. Research Search Capacity
* **Screening 100 Candidates $\times$ 50 Seeds (5,000 matches)**: Executes in **`~6.2 seconds`**.
* **Screening 1,000 Candidates $\times$ 50 Seeds (50,000 matches)**: Executes in **`~61.5 seconds`**.
* **Conclusion**: Simulation throughput is **no longer a bottleneck**. The research engine is primed for high-dimensional strategy space exploration.
