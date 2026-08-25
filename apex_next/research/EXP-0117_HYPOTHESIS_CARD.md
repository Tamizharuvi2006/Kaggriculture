# 🧪 EXP-0117: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0117`  
> **Target Baseline**: `APEX-3.5-PROD` (`submission.py`, SHA256 `78738c1b...`)  
> **Challenger Identifier**: `CAND-GPU-2979` (`apex_next/research/EXP-0117/candidate/candidate_submission.py`)  
> **Variable Family**: `Inventory_Liquidity` (Single-variable isolation)  
> **Discovery Source**: GPU Fast Engine Mass Screening (Stage 3 Grid Search)

---

## 1. Formal Mechanism Hypothesis

> *"Increasing the APEX 3.5 ongoing safe cash buffer floor from **$400 $\rightarrow$ $500$** provides additional liquidity insurance during Day-12/14 market dips, preventing worker stalling and crop planting delays without compromising overall compounding reinvestment velocity or triggering excess PASS turns."*

---

## 2. Parameter Mutation

| Parameter | Baseline (APEX 3.5) | Challenger (EXP-0117) | Rationale |
| :--- | :--- | :--- | :--- |
| `safe_buffer` (ongoing, post-Land 3) | `$400.0` | **`$500.0`** | +$100 liquidity margin against market price slump. |
| `sell_timing` | `step % 24 == 23` | `step % 24 == 23` | Invariant preserved. |
| `rebound_threshold` | `$120.0` | `$120.0` | Invariant preserved. |
| `reinvestment_rate` | 100% | 100% | Invariant preserved. |

---

## 3. Pre-Registered 6-Dimension Promotion Gates

To be promoted to production, `EXP-0117` must clear all 6 gates on the frozen holdout suite (`HOLDOUT_V1_N100`, $N = 100$, seat-balanced):

1. **Win Rate**: $\Delta \text{WR} \ge +2.5\%$ vs `APEX 3.5` ($p < 0.05$).
2. **Mean Wealth**: $\Delta \mu_{\text{MCV}} \ge +\$2{,}000$ ($p < 0.05$).
3. **Volatility**: $\sigma_{\text{cand}} / \sigma_{\text{base}} \le 1.10$.
4. **Tail Risk**: $\text{MCV}_{p05}(\text{cand}) \ge \text{MCV}_{p05}(\text{base})$.
5. **PASS Inactivity**: $\Delta \text{PASS} \le +0.2\%$, max consecutive PASS turns $\le 3$.
6. **Step Latency**: Mean $\le 20\text{ms}$, Max $\le 200\text{ms}$.

---

## 4. Single-Shot Protocol Contract
- No post-hoc parameter adjustments.
- If any gate fails, `EXP-0117` is permanently archived as `FALSIFIED_REJECTED`.
