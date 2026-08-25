# 🧪 EXP-0118: PRE-REGISTERED HYPOTHESIS CARD

> **Experiment ID**: `EXP-0118`  
> **Target Baseline**: `APEX-3.5-PROD` ([`submission.py`](file:///D:/kaggriculture/submission.py), SHA256 `78738c1b...`)  
> **Target Archetype**: `LATE_MILK_TIMING` (Priority Engine Rank #1)  
> **Sole Variable Family**: `Timing` (Single-variable isolation)  
> **Evidence Source**: [`reports/late_milk_evidence.json`](file:///D:/kaggriculture/reports/late_milk_evidence.json) (400 liquidation events, 12.0-step shed latency)

---

## 1. Verified Mechanism & Empirical Evidence

In `APEX 3.5`, Regime 2 (Cash-Flushed) enforces a strict holding condition:
```python
if p_milk >= 115.0 and milk_in_shed >= 4:
  market_orders.append(["SELL", "MILK", milk_in_shed])
```
* **Measured Bottleneck**: Cows generate milk at $0.5$ units/step. Waiting for `milk_in_shed >= 4` causes milk to sit in the shed for **$12.0$ steps** on average.
* **Market Impact**: This delay incurs **$2.62/batch price slippage** before clearance, creating a modest but consistent **~$52 to $150 revenue deficit** per match.

---

## 2. Formal Mechanism Hypothesis

> *"Lowering the Regime 2 milk liquidation batch threshold from **`milk_in_shed >= 4` $\rightarrow$ `milk_in_shed >= 2`** during the late-game window (steps $\ge 450$) liquidates milk ~12 turns earlier at prevailing top-of-cycle prices, capturing additional realized milk revenue without causing strawberry harvesting delays or increasing PASS action volatility."*

---

## 3. Pre-Registered Bounded Parameter Space (for GPU Screening)

| Parameter | Baseline (APEX 3.5) | Bounded Search Space |
| :--- | :--- | :--- |
| `late_milk_batch_threshold` | `4` | `[1, 2, 3]` |
| `late_milk_activation_step` | `0` (Always 4) | `[400, 450, 500, 550]` |
| `late_milk_min_price` | `$115.0` | `[$100.0, $115.0, $125.0]` |

---

## 4. Pre-Registered 6-Dimension Promotion Gates

To be promoted to production, `EXP-0118` must clear all 6 gates on the frozen holdout suite (`HOLDOUT_V1_N100`, $N \ge 100$, seat-balanced):

1. **Win Rate**: $\Delta \text{WR} \ge +2.5\%$ vs `APEX 3.5` ($p < 0.05$).
2. **Mean Wealth**: $\Delta \mu_{\text{MCV}} \ge +\$2{,}000$ ($p < 0.05$).
3. **Volatility**: $\sigma_{\text{cand}} / \sigma_{\text{base}} \le 1.10$.
4. **Tail Risk**: $\text{MCV}_{p05}(\text{cand}) \ge \text{MCV}_{p05}(\text{base})$.
5. **PASS Inactivity**: $\Delta \text{PASS} \le +0.2\%$, max consecutive PASS turns $\le 3$.
6. **Step Latency**: Mean $\le 20\text{ms}$, Max $\le 200\text{ms}$.

---

## 5. Single-Shot Protocol Contract
- No post-hoc tuning.
- Candidate will be screened via GPU search $\rightarrow$ best candidate cluster tested against Gate 1 $\rightarrow$ if Gate 1 fails, candidate is permanently falsified and halted.
