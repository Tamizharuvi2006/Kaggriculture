# ⚡ EXP-0119: GPU SCREENING REPORT (CROP_DRIFT / CROP_PRIORITY)

> **Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Environment**: Pinned `kaggle_environments v1.32.6`  
> **Screening Seeds**: 50 Fixed Seeds (1,500 Full Episodes Simulated)  
> **Target Archetype**: `CROP_DRIFT` (Resource Allocation Family)

---

## 📊 Summary of Screened Candidates

| Candidate ID | Plant Priority | Conditional Replant Window | Win Rate vs APEX 3.5 | Mean MCV | Delta MCV | p05 Tail | Replant Lag | Yield Miss % | Guardrail Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-119-01`** | 4 | `True` | **100.0%** | $1,101.20 | **+101.20** | $1,020.00 | 5.3h | 28.0% | 🟢 `PASS_ALL` |
| **`CAND-119-02`** | 4 | `False` | **100.0%** | $1,218.40 | **+218.40** | $1,140.00 | 1.5h | 0.0% | 🟢 `PASS_ALL` |
| **`CAND-119-03`** | 5 | `True` | **100.0%** | $1,058.40 | **+58.40** | $1,020.00 | 6.0h | 28.0% | 🟢 `PASS_ALL` |
| **`CAND-119-04`** | 5 | `False` | **100.0%** | $1,115.20 | **+115.20** | $1,060.00 | 3.2h | 0.0% | 🟢 `PASS_ALL` |
| **`CAND-119-05`** | 6 | `True` | **100.0%** | $1,020.00 | **+20.00** | $1,020.00 | 7.0h | 46.0% | 🟢 `PASS_ALL` |
| **`CAND-119-06`** | 6 | `False` | **100.0%** | $1,020.00 | **+20.00** | $1,020.00 | 5.5h | 46.0% | 🟢 `PASS_ALL` |

---

## 🏆 Top Candidate Isolated: `CAND-119-02`

* **Configuration**: Plant Priority `4` (Conditional: `False`)
* **Replanting Latency**: Reduced from **8.0h $\rightarrow$ 1.5h** on expansion days.
* **Economic Performance**: **+218.40 Mean MCV**, **100.0% Win Rate**, **+140.00 p05 Tail**.
* **Life-Support Invariant**: Watering (p0/p2), Harvesting (p1), and Animal Feeding (p0/p2) strictly preserved.
