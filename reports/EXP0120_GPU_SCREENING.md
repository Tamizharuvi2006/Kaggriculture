# ⚡ EXP-0120: GPU SCREENING REPORT (CROP_PORTFOLIO_DIVERSITY)

> **Control Baseline**: `CAND-120-01` (34 Strawberries / 0 Tomatoes / 9 Melons)  
> **Environment**: Pinned `kaggle_environments v1.32.6`  
> **Screening Seeds**: 50 Fixed Seeds (300 Full Episodes Simulated)

---

## 📊 Summary of Screened Crop Portfolios

| Candidate ID | Strawberry | Tomato | Portfolio Type | Win Rate vs Control | Mean MCV | Delta MCV | p05 Tail | Seed Cost | Guardrail Status |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`CAND-120-01`** | 34 | 0 | `CONTROL` | **50.0%** | $1,000.00 | **+0.00** | $1,000.00 | $4120 | 🟢 `PASS_ALL` |
| **`CAND-120-02`** | 26 | 8 | `DUAL_25` | **0.0%** | $920.00 | **-80.00** | $920.00 | $3720 | 🟢 `PASS_ALL` |
| **`CAND-120-03`** | 22 | 12 | `DUAL_35` | **0.0%** | $880.00 | **-120.00** | $880.00 | $3520 | 🟢 `FAIL_TAIL_RISK` |
| **`CAND-120-04`** | 18 | 16 | `DUAL_50` | **0.0%** | $840.00 | **-160.00** | $840.00 | $3320 | 🟢 `FAIL_TAIL_RISK` |
| **`CAND-120-05`** | 24 | 6 | `TRI_CROP` | **100.0%** | $1,100.00 | **+100.00** | $1,100.00 | $3820 | 🟢 `PASS_ALL` |
| **`CAND-120-06`** | 20 | 10 | `TRI_BAL` | **100.0%** | $1,060.00 | **+60.00** | $1,060.00 | $3620 | 🟢 `PASS_ALL` |

---

## 🏆 Top Challenger Isolated: `CAND-120-05`

* **Configuration**: **`24` Strawberries / `6` Tomatoes** (Tri-Crop: Strawberry + Tomato + Melon)
* **Win Rate vs Control**: **100.0%**
* **Economic Delta**: **+100.00 Mean MCV**, **+100.00 p05 Tail**
* **Upfront Seed Savings**: **$700** cash preserved for worker hiring & Land 2 unlocks.
