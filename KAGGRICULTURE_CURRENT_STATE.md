# 🏛️ KAGGRICULTURE CURRENT STATE & RESEARCH SNAPSHOT

**Document Updated**: August 11, 2026  
**Primary Source**: Real Kaggle Tournament Replay Population (43 Matches / 86 Trajectories), 35-Phase Empirical Research Program, Live Ladder Manifests.

---

## 📊 1. GROUND-TRUTH 3000+ KAGGLE POPULATION INVARIANTS (Phase 34)

* **Sample**: 43 Full 720-Step Real Kaggle Matches (86 Player Trajectories) from 2600–3200+ Competition Episodes.
* **Score & Margin**:
  - **Winners Mean Final Wealth**: **$80,860.86**
  - **Losers Mean Final Wealth**: **$56,627.00**
  - **Mean Victory Margin**: **+$24,233.86**
* **The Clearance Paradox**:
  - **Winners Clearance Strawberry Sales**: **13.3 units**
  - **Losers Clearance Strawberry Sales**: **32.6 units (2.5x more!)**
  - *Key Finding*: Dumping inventory on clearance boundaries (`step % 24 == 23`) depresses realized prices. Winners preserve large full-priced batch sales (8.4 units/batch @ $141.08/unit vs $125.82/unit for losers).
* **Early Reinvestment Dynamics**:
  - Days 1–11: Winners intentionally run **lower liquid cash** (-$150 to -$240 vs losers) by aggressively reinvesting every dollar into Cow feed and Land #2/3.
  - Day 15 (Step 360): The capital deployment triggers an explosive inflection (+**$2,684 lead**), compounding to +$6,593 at Day 21 and +$24,233 at Day 30.
* **3-Quadrant Expansion Ceiling**:
  - **95.3% of 3000+ Winners NEVER buy Land #4** (Land #4 purchase rate is only 4.7%).
  - Land #4 ($10,000 capex) requires ~12 full days (288 steps) to break even; purchasing it in a 30-day game causes an immediate -$3,300 to -$4,100 wealth collapse.
* **Dual-Engine Revenue Standard**:
  - 3000+ Winners generate **$73,522 from Strawberry** AND **$62,139 from Milk**.

---

## 🔬 2. MARKET EQUILIBRIUM & CROSS-COMMODITY PRICING REGIMES (Phase 35)

* **Physical Production Invariance**:
  - Across holdout test seeds, APEX 3.4 produces identical volume (616 Strawberry units sold, 65 harvest actions, 27 fertilizer applications, 333 worker actions across both wins and losses).
* **Price Realization Divergence**:
  - **Winning Seeds**: Base Strawberry = **$165.16/u** | Base Milk = **$131.63/u** | Realized Strawberry = **$162.57/u**.
  - **Losing Seeds**: Base Strawberry = **$158.43/u** | Base Milk = **$155.86/u** | Realized Strawberry = **$151.52/u**.
* **Cross-Commodity Regimes**:
  - Kaggriculture's Markov pricing generates complementary market regimes. Losing seeds are High-Milk ($155.86/u) regimes where opponents who scale milk production accumulate compounding leverage.

---

## 🏛️ 3. REPOSITORY GOVERNANCE & BENCHMARK HIERARCHY

* 🛡️ **Kaggle Live Candidate**: **Ref 55421857** (`generalization_pipeline/submission_candidate_apex33.py`) — **ACTIVE & UNTOUCHED**.
* 🛡️ **Historical Master Champion Baseline**: **Ref 55249106** (`submission.py`, 1479.8 public score) — **IMMUTABLE & PROTECTED**.
* 🎯 **New Research Reference**: **Ground-Truth Real Kaggle 3000+ Winner Empirical Population** (V4.1 cleanly decoupled from research discovery loop).
* 🔒 **Local Research Candidate**: **APEX 3.4** (`generalization_pipeline/submission_candidate_apex34.py`) — **FROZEN LOCALLY** (Not submitted).

---

## ⚙️ 4. ENVIRONMENT PARAMETERS & SAFETY INVARIANTS

1. **Environment Parity**: `townCenterSellInterval = 24` (24 steps/day, 720 steps total).
2. **Rule Zero**: APEX must NEVER explore capital-consuming actions (`BUY_SEED`, `BUY_LAND`, `HIRE`, `BUY_ANIMAL`).
3. **Zero Synthetic Orders**: APEX must never inject artificial fallback sales.
4. **Monolithic Submissions**: 100% self-contained single-file Python scripts (<100ms/turn execution).
