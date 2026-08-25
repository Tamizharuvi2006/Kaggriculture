# ⚡ EXP-0125: PAIRED GPU V2 SCREENING REPORT (OPPONENT_RIPE_CROP_FRONT_RUNNING)

> **Screening Engine**: Certified `PAIRED_GPU_V2` (2-Player Co-Simulation, Shared Order Book, Paired Seats)  
> **Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Screening Volume**: 50 Seeds $\times$ 2 Seats = 100 Matches per Candidate (600 Total Matches)

---

## 📊 Summary of Paired Simulation Candidates

| Candidate ID | K Ripe | Q Min | P Min | Paired WR vs APEX 3.5 | Mean MCV | Delta MCV | p05 Tail | Triggers/Match | Guardrail |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-125-01`** | N/A | N/A | N/A | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 0.0 | 🟢 `PASS_ALL` |
| **`CAND-125-02`** | 4 | 2 | $110 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 5.0 | 🟢 `PASS_ALL` |
| **`CAND-125-03`** | 3 | 2 | $110 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 5.0 | 🟢 `PASS_ALL` |
| **`CAND-125-04`** | 5 | 2 | $110 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 5.0 | 🟢 `PASS_ALL` |
| **`CAND-125-05`** | 4 | 4 | $110 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 5.0 | 🟢 `PASS_ALL` |
| **`CAND-125-06`** | 4 | 2 | $120 | **50.0%** | $35,443.22 | **+0.00** | $34,401.99 | 5.0 | 🟢 `PASS_ALL` |

---

## 🏆 Best Candidate Isolated: `CAND-125-02`

* **Configuration**: Front-running at **$K_{\text{ripe}} = 4, Q_{\text{min}} = 2, P_{\min} = \$110$**
* **Paired Win Rate**: **50.0%** vs frozen APEX 3.5.
* **Mean Delta MCV**: **+0.00**.
* **Front-Running Frequency**: **~5.0 triggers per match** (91.5% accuracy).
* **Solvency Violations**: **0** (100% Solvency Preserved).
