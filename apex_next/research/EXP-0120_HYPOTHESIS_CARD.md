# 🧪 EXP-0120: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0120`  
> **Target Baseline**: `APEX-3.5-PROD` ([`submission.py`](file:///D:/kaggriculture/submission.py), SHA256 `78738c1b...`)  
> **Target Archetype**: `CROP_PORTFOLIO_DIVERSITY` (OPP-DIFF-2 Rank #1)  
> **Sole Variable Family**: `Resource_Allocation` (Single-variable isolation)  
> **Evidence Source**: [`reports/EXP0120_CROP_PORTFOLIO_AUDIT.json`](file:///D:/kaggriculture/reports/EXP0120_CROP_PORTFOLIO_AUDIT.json)

---

## 1. Verified Mechanism & Empirical Evidence

In `APEX 3.5`, the crop portfolio is a pure **Strawberry mono-culture** (`strawberries = 34`, `tomatoes = 0`):
* **Identified Vulnerability**: Strawberry seed cost is high ($100/seed) with late initial harvest (Day 10). When Strawberry market price enters a slump ($P < \$100$), APEX suffers cash starvation.
* **Causal Hedge**: Tomato seed cost is **50% cheaper ($50/seed)**, with first harvest on **Day 8** (2 days earlier). Cross-correlation with Strawberry price is statistically zero ($r = -0.015$).
* **Elite Precedent**: 68.4% of tournament winners (>1400 TrueSkill) utilize a multi-crop portfolio to stabilize reinvestment velocity.

---

## 2. Formal Mechanism Hypothesis

> *"Allocating a bounded portion (25%–35%) of crop land to Tomato (`strawberries = 22–26`, `tomatoes = 8–12`) reduces upfront seed expenditure by $400–$600, captures early revenue at Day 8 to accelerate farm expansion, and provides independent cash flow ($\text{Corr} \approx 0.0$) during Strawberry price dips without eroding top-line compounding wealth or increasing PASS volatility."*

---

## 3. Pre-Registered Bounded Parameter Space (for GPU Screening)

| Candidate ID | Strawberry Target | Tomato Target | Opening Melon Share | Portfolio Strategy Profile |
| :--- | :---: | :---: | :---: | :--- |
| **`CAND-120-01`** | `34` | `0` | `9` | 100% Strawberry Mono-culture (APEX 3.5 Baseline) |
| **`CAND-120-02`** | `26` | `8` | `9` | 75% Strawberry / 25% Tomato Dual-Crop |
| **`CAND-120-03`** | `22` | `12` | `9` | 65% Strawberry / 35% Tomato Dual-Crop |
| **`CAND-120-04`** | `18` | `16` | `9` | 50% Strawberry / 50% Tomato Dual-Crop |
| **`CAND-120-05`** | `24` | `6` | `14` | Tri-Crop: Strawberry + Tomato + Expanded Melon |
| **`CAND-120-06`** | `20` | `10` | `14` | Tri-Crop: Balanced Multi-Crop Portfolio |

*Total Frozen Grid*: Exactly **6 structured configurations**.

---

## 4. Pre-Registered 6-Dimension Promotion Gates

To be promoted to production, `EXP-0120` must clear all 6 gates on the frozen holdout suite (`HOLDOUT_V1_N100`, $N \ge 100$, seat-balanced):

1. **Win Rate**: $\Delta \text{WR} \ge +2.5\%$ vs `APEX 3.5` ($p < 0.05$).
2. **Mean Wealth**: $\Delta \mu_{\text{MCV}} \ge +\$2{,}000$ ($p < 0.05$).
3. **Volatility**: $\sigma_{\text{cand}} / \sigma_{\text{base}} \le 1.10$.
4. **Tail Risk**: $\text{MCV}_{p05}(\text{cand}) \ge \text{MCV}_{p05}(\text{base})$.
5. **PASS Inactivity**: $\Delta \text{PASS} \le +0.2\%$, max consecutive PASS turns $\le 3$.
6. **Step Latency**: Mean $\le 20\text{ms}$, Max $\le 200\text{ms}$.

---

## 5. Single-Shot Protocol Contract
- Screen the 6 pre-registered candidates on RTX 4050 $\rightarrow$ submit the top candidate to official Gate 1 on pinned `kaggle_environments v1.32.6`.
- If Gate 1 fails $\rightarrow$ candidate halted immediately.
