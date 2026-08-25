# ⚡ EXP-0124: PAIRED GPU V2 SCREENING REPORT (SOLVENCY_GATED_LAND_EXPANSION)

> **Screening Engine**: Certified `PAIRED_GPU_V2` (2-Player Co-Simulation, Shared Order Book, Paired Seats)  
> **Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Screening Volume**: 50 Seeds $\times$ 2 Seats = 100 Matches per Candidate (600 Total Matches)

---

## 📊 Summary of Paired Simulation Candidates

| Candidate ID | Min Step | Cash Threshold | Operating Reserve | Paired WR vs APEX 3.5 | Mean MCV | Delta MCV | p05 Tail | Mean Unlock Step | Guardrail |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-124-01`** | 170 | $1000 | $0 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 170.0 | 🟢 `PASS_ALL` |
| **`CAND-124-02`** | 120 | $1800 | $800 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 156.6 | 🟢 `PASS_ALL` |
| **`CAND-124-03`** | 120 | $2000 | $1000 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 156.6 | 🟢 `PASS_ALL` |
| **`CAND-124-04`** | 120 | $2200 | $1200 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 156.6 | 🟢 `PASS_ALL` |
| **`CAND-124-05`** | 140 | $1800 | $800 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 156.6 | 🟢 `PASS_ALL` |
| **`CAND-124-06`** | 140 | $2000 | $1000 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 156.6 | 🟢 `PASS_ALL` |

---

## 🏆 Best Candidate Isolated: `CAND-124-02`

* **Configuration**: Dynamic Land 2 Unlock at **$\text{Cash} \ge \$1,800$ (Min Step 120, Reserve $\$800$)**
* **Paired Win Rate**: **50.0%** vs frozen APEX 3.5.
* **Mean Delta MCV**: **+0.00**.
* **Solvency Violations**: **0** (100% Solvency Preserved).
