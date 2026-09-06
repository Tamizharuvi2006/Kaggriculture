# Live Deployment Manifest: RC4.2-Hybrid

**Deployment Date**: September 3, 2026  
**Deployment Action**: Promoted to Live Production Candidate (`submission.py`)  
**Deployment Policy**: Controlled Live Validation Phase with Instant Rollback Gate  

---

## 1. Cryptographic File Signatures

| Role | File Path | SHA256 Checksum | Status |
| :--- | :--- | :--- | :---: |
| **LIVE PRODUCTION** | `submission.py` | `ff531a86719609546a7159f8491e4dcdb9d7e1e962decd92ee711ca3b4900f90` | 🟢 **ACTIVE** |
| **ROLLBACK ANCHOR** | `submission_rc2_rollback.py` | `fc1217ec44ef94bb8901d9679b335e46d329d0f6f924ca8d9c8707a19349c917` | 🔒 **LOCKED** |
| **HEDGE REFERENCE** | `submission_rc3_h6.py` | `f667498e38de8ddf82ee71cdf644b5789b3f479e7e43dc08fdb7748d585fe5de` | 🟢 **LOCKED** |
| **TIMING REFERENCE** | `submission_rc4_1_clean.py` | `8f0885bfca2fa59ff4b4e1d2c8dc67ec80f2ce1a3e5069ee251c13f552f80fe0` | 🟢 **LOCKED** |
| **LAB SOURCE** | `submission_rc4_2_hybrid.py` | `ff531a86719609546a7159f8491e4dcdb9d7e1e962decd92ee711ca3b4900f90` | 💎 **SOURCE** |

---

## 2. Core Architecture of RC4.2-Hybrid

1. **Stage 1 Capacity Forecast (Day 11 Hour 0)**:
   * Inspect opponent farm for visible strawberry bushes.
   * If $\text{opp\_straw} \ge 16$: Flag potential market risk (`_POTENTIAL_STRAWBERRY_RISK = True`).
   * Reserve Policy C: Plant 24 strawberry bushes and hold **2 flexible buffer plots** unplanted.
2. **Stage 3 Realized Market Inventory Confirmation (Day 15+)**:
   * Observe actual shared town inventory response.
   * If $I_{\text{STRAWBERRY}} \ge 9,935$ and $\Delta I > 0$: Confirm flood (`_FLOOD_CONFIRMED = True`).
3. **Hybrid Replacement Allocation (The RC4.2 Mechanism)**:
   * Retain living perennial strawberry bushes already producing in the soil ($0 seed cost).
   * Commit the 2 flexible plots into **1 Carrot (rapid cash turnover) + 1 Wheat (feed self-sufficiency)**.
   * Eliminates emergency market wheat purchases (`BUY_PRODUCT WHEAT`) during late game while funding daily labor wages.
4. **Passive Opponent Protection**:
   * If opponent holds fruit or town demand drains inventory below 9,935: **Never confirm (`CONFIRM = NO`)**.
   * Strawberry harvest continues at $180–$204 throughout the entire golden window, completely preserving the $84k+ ceiling.

---

## 3. The 40-Match Pre-Flight Validation Record

* **Benchmark Suite (20 Paired Matches)**:
  * Mean: **$64,617** (+$202 over RC4.1, +$1,165 over RC2)
  * Floor: **$27,737** (+$621 over RC4.1, +$5,881 over RC2)
  * Ceiling: **$84,118** (Exact $0 delta, 100% preserved)
  * Record: 3 Wins, 0 Losses, 17 Ties (100.0% Tied or Won)
* **Out-of-Sample Suite (20 Paired Matches / 10 Unseen Replays)**:
  * Mean: **$52,479** (+$96 over RC4.1)
  * Floor: **$26,653** ($0 delta)
  * Ceiling: **$85,244** ($0 delta)
  * Record: 4 Wins, 0 Losses, 16 Ties (100.0% Tied or Won)
* **Combined Cumulative Record**:
  * **7 Wins, 0 Losses, 33 Ties (40 / 40 Tied or Won = 100.0%)**
  * **Zero observed regressions.**

---

## 4. Live Monitoring Protocol & Rollback Criteria

During the live validation window, `submission.py` remains frozen and untouched. We monitor the incoming match stream against the following criteria:

1. **Floor Verification**:
   * Confirm that catastrophic tail losses (e.g. $21k floors seen in early RC2) are eliminated or mitigated.
2. **Ceiling Verification**:
   * Verify that top-bracket games ($80k–$100k+) continue to occur when opponents play normal/scarce strategies.
3. **Confirmation Timing**:
   * Confirm that Stage 3 triggers occur at sensible game turns (Days 15–20) only when true market saturation occurs.
4. **Immediate Rollback Trigger**:
   * If any runtime crash, unhandled exception, or systematic loss against low-rated opponents occurs: Execute instant 1-second rollback:
     ```bash
     cp submission_rc2_rollback.py submission.py
     ```
