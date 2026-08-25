# ⚡ EXP-0121: PAIRED GPU V2 SCREENING REPORT (LAND_EXPANSION_PACING)

> **Screening Engine**: Certified `PAIRED_GPU_V2` (2-Player Co-Simulation, Shared Order Book, Paired Seats)  
> **Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Screening Volume**: 50 Seeds $\times$ 2 Seats = 100 Matches per Candidate (600 Total Matches)

---

## 📊 Summary of Paired Simulation Candidates

| Candidate ID | Min Step | Cash Threshold | Paired WR vs APEX 3.5 | Mean MCV | Delta MCV | p05 Tail | Mean Unlock Step | Guardrail |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-121-01`** | 170 | $1000 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 170.0 | 🟢 `PASS_ALL` |
| **`CAND-121-02`** | 120 | $1100 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 131.0 | 🟢 `PASS_ALL` |
| **`CAND-121-03`** | 120 | $1200 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 131.0 | 🟢 `PASS_ALL` |
| **`CAND-121-04`** | 130 | $1100 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 136.6 | 🟢 `PASS_ALL` |
| **`CAND-121-05`** | 140 | $1100 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 142.2 | 🟢 `PASS_ALL` |
| **`CAND-121-06`** | 144 | $1000 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | Step 144.4 | 🟢 `PASS_ALL` |

---

## 🏆 Best Candidate Isolated: `CAND-121-02`

* **Configuration**: Dynamic Land 2 Unlock at **$\text{Cash} \ge \$1,100$ (Min Step 120)**
* **Paired Win Rate**: **50.0%** vs frozen APEX 3.5.
* **Mean Delta MCV**: **+0.00**.
* **Unlock Velocity**: Land 2 unlocked at **Step 131.0** (saving ~35 steps of idle cash).
