# 📜 Phase 97: Symmetric-Game First-Divergence Reconstruction Report

> **Dataset Scope**: **25 Symmetric Near-Parity Matches** (8 Class B/F 3100+ Champion Replays + 17 Live Razor-Thin Loss Seeds).
> **Key Finding**: First divergence (s_div) occurs at **Average Step 259.5 (Day 11.8)**.
> **Category Breakdown**:
> - **Cat 1 & 2 (Clearance Timing & Town Preemption)**: **2 / 25 matches (8.0%)**
> - **Cat 4 (Inventory Carryover / Latency)**: **7 / 25 matches (28.0%)**
> - **Cat 6 (True Unavoidable Parity / Sub-$100 Split)**: **4 / 25 matches (16.0%)**

---

## 📊 1. Master Divergence Dissection Table

| Match Identifier | Seed | Winner Wealth ($) | Loser Wealth ($) | Net Margin ($) | Divergence Step (s_div) | Causal Divergence Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `90561400.json` | `1678842161` | $150,620.00 | $150,620.00 | **$0.00** | Step 719 (D30:H23) | `Cat 6: True Unavoidable Parity (Sub-$100 Split)` |
| `90561415.json` | `1682794631` | $139,989.00 | $135,701.00 | **$4,288.00** | Step 282 (D12:H18) | `Cat 4: Inventory Carryover / Worker Latency` |
| `90562249.json` | `1750711383` | $139,165.00 | $139,165.00 | **$0.00** | Step 719 (D30:H23) | `Cat 6: True Unavoidable Parity (Sub-$100 Split)` |
| `90562250.json` | `1477162212` | $120,521.00 | $117,445.00 | **$3,076.00** | Step 360 (D16:H0) | `Cat 4: Inventory Carryover / Worker Latency` |
| `90562264.json` | `1537923793` | $140,226.00 | $140,187.00 | **$39.00** | Step 698 (D30:H2) | `Cat 6: True Unavoidable Parity (Sub-$100 Split)` |
| `91153990.json` | `1331713741` | $120,199.00 | $119,551.00 | **$648.00** | Step 239 (D10:H23) | `Cat 1: Clearance Sizing / Order Difference` |
| `91154152.json` | `298531191` | $92,684.00 | $91,903.00 | **$781.00** | Step 713 (D30:H17) | `Cat 4: Inventory Carryover / Worker Latency` |
| `91154171.json` | `2021127840` | $65,343.00 | $63,399.00 | **$1,944.00** | Step 239 (D10:H23) | `Cat 1: Clearance Sizing / Order Difference` |
| `Seed_92710604` | `92710604` | $82,937.00 | $81,599.00 | **$1,338.00** | Step 159 (D7:H15) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92659893` | `92659893` | $84,940.00 | $84,885.00 | **$55.00** | Step 294 (D13:H6) | `Cat 6: True Unavoidable Parity (Sub-$100 Split)` |
| `Seed_92820867` | `92820867` | $57,918.00 | $57,266.00 | **$652.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92744887` | `92744887` | $63,331.00 | $60,702.00 | **$2,629.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92685417` | `92685417` | $84,606.00 | $83,901.00 | **$705.00** | Step 294 (D13:H6) | `Cat 4: Inventory Carryover / Worker Latency` |
| `Seed_92663703` | `92663703` | $128,222.00 | $123,548.00 | **$4,674.00** | Step 294 (D13:H6) | `Cat 4: Inventory Carryover / Worker Latency` |
| `Seed_92665598` | `92665598` | $94,272.00 | $86,959.00 | **$7,313.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92682596` | `92682596` | $100,098.00 | $96,100.00 | **$3,998.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92670343` | `92670343` | $81,436.00 | $80,375.00 | **$1,061.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92677877` | `92677877` | $53,510.00 | $52,059.00 | **$1,451.00** | Step 169 (D8:H1) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92676926` | `92676926` | $89,780.00 | $87,921.00 | **$1,859.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92662787` | `92662787` | $118,903.00 | $116,111.00 | **$2,792.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92680700` | `92680700` | $118,771.00 | $114,439.00 | **$4,332.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92662754` | `92662754` | $87,354.00 | $86,891.00 | **$463.00** | Step 294 (D13:H6) | `Cat 4: Inventory Carryover / Worker Latency` |
| `Seed_92684467` | `92684467` | $64,575.00 | $63,971.00 | **$604.00** | Step 294 (D13:H6) | `Cat 4: Inventory Carryover / Worker Latency` |
| `Seed_92792740` | `92792740` | $125,926.00 | $121,887.00 | **$4,039.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |
| `Seed_92678835` | `92678835` | $77,093.00 | $74,203.00 | **$2,890.00** | Step 72 (D4:H0) | `Cat 5: Early Reinvestment / Land Expansion Timing` |

---

## 🔍 2. Micro-Mechanic Takeaways & Reconciliation

1. **Early Divergence Is the Dominant Driver (Cat 5 @ 48.0%)**:
   - In nearly half of all symmetric matches (12/25), first divergence occurs early between **Day 4 (Step 72)** and **Day 7 (Step 170)**.
   - Securing a single extra unit of liquidity before Day 7 enables unlocking Land #2 at Step 168 instead of Step 171, compounding into 2–3 additional Strawberry harvests over the remaining 550 turns.

2. **Worker Inventory Drop Latency (Cat 4 @ 28.0%)**:
   - In 28% of matches (7/25), divergence occurs between Days 12–16 (Steps 282–360) when crops harvested on Turn 22 remain in worker backpacks rather than reaching the shed before the Turn 23 clearance window.
   - This delays cash realization by 24 turns, causing minor recurring price slips.

3. **True Stochastic Nash Parity (Cat 6 @ 16.0%)**:
   - In 16% of matches, both agents execute identical flawless play and split the economic pie down to pennies ($0 to $55 margin).

---

## 🏛️ Policy & Submission Governance

- 🛡️ **APEX 3.5 Candidate (`submission_candidate_apex35.py`) remains 100% FROZEN on Kaggle (`Ref 55483322`)**.
- Zero code modifications, no parameter tuning, and **strictly NO git push without permission**.
