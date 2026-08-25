# 🧪 EXP-0115 — HYPOTHESIS CARD (Third Research Cycle)

**Status**: FORMULATED — awaiting gate execution
**Parent**: EXP-0114 (FALSIFIED — over-suppression of sales, cash starvation)
**Origin**: Buy-path diagnostic (8 real loss seeds)

---

## Evidence Chain (why this experiment exists)

1. **EXP-0113 falsified**: exit-timing suppression (drift ≤ −30% ∧ below-MA) — inert (fired 5/46 seeds).
2. **EXP-0114 falsified**: below-MA sell suppression — catastrophic over-suppression (5,725 orders, WR 6.5%, ΔMCV −8,126). Selling below the MA is load-bearing for the champion's cash cycles.
3. **Buy-path diagnostic** (8 loss seeds, 122 collapse agent-steps, ~1% of steps): the champion deploys capital **disproportionately during confirmed collapse windows**:
   - BUY_SEED:STRAWBERRY: **26/123 (21%)**
   - BUY_SEED:MELON: **8/38 (21%)**
   - BUY_ANIMAL:COW: **34/100 (34%)**, BUY_ANIMAL:SHEEP: **24/68 (35%)**
4. The named rival hypothesis from the EXP-0114 card: *the weakness is not sale timing — it is re-entry (rebuying/replanting into collapse-trough prices).*

---

## Hypothesis (single variable family: `Capital_Deployment`)

> **Mechanism**: Deferred re-entry. While a decisive product (STRAWBERRY/MELON) is in a confirmed SUPPLY_COLLAPSE (3-step price drift ≤ −30% — the fingerprint-calibrated regime threshold), drop BUY_SEED orders for the collapsing product. Re-arm purchases when the 3-step drift turns **≥ 0** (recovery confirmed) or after a hard cap of **48 steps** (2 days) — bounding the risk of missing the planting window. Farmer actions, sales, animals, and all other orders are untouched.

**Why this differs from the falsified parents**: (a) it acts on the **buy** side (re-entry), not the sell side — sell-side suppression starved cash (EXP-0114); (b) it uses the calibrated regime drift trigger, NOT the below-MA filter that fired 45/46 seeds; (c) deferring a seed purchase only delays spending — it cannot starve cash, and the champion re-issues buys on recovery (no PASS, no farmer change).

**Expected upside**: avoid buying seeds of a crashing crop at the top of its decline → cash preserved for the recovery wave; WR +2.5%, MCV +2,000 on frozen holdout.
**Expected downside (must be checked)**: missed planting windows if recovery never comes within the 48-step cap (bounded by cap) — planting delay shifts the second-crop harvest later; p05 tail gate checks this.
**Named rival** (if EXP-0115 fails): the collapse-window purchases are **schedule-driven** (late-game expansion) and correlate with collapses only by timing — capital deployment timing is not the mechanism; the SUPPLY_COLLAPSE weakness is then attributed to **milk/wool sale timing during collapse** (EXP-0116).

---

## Candidate spec (Phase 4)

- **Variable family**: `Capital_Deployment` (first experiment in this family)
- **Baseline**: `submission.py` (APEX 3.6 PROD, code_hash `f10bb5ea…`) — IMMUTABLE
- **Modification surface**: one market-order filter (drop BUY_SEED of collapsing product); wrapper module identical in structure to EXP-0113/0114 candidates
- **Parameters**: `COLLAPSE_DRIFT = −0.30`, `REARM_DRIFT = 0.0`, `HOLD_CAP_STEPS = 48`, products STRAWBERRY/MELON

## Gates (Phase 5)

| Gate | Suite | Pass rule |
| :--- | :--- | :--- |
| 1. Exact Replay | 46 real loss seeds × 2 seats | ≥60% WR |
| 2. Historical Suite | 50 fixed seeds × 2 seats (10 groups × 5) | ≥75% overall, no group <60% |
| 3. Frozen Holdout | HOLDOUT_V1_N100, single shot | paired vs baseline |
| 4. Statistical Judge | 6 dimensions | ΔWR ≥ +2.5%, ΔMCV ≥ +2,000, σ ≤ 1.10, p05 ≥ base, added PASS ≤ 3, latency ≤ 20/200ms |

**Harness**: seat-balanced double-run, determinism verified (byte-identical reruns). Falsification is a good outcome — it yields EXP-0116 (milk/wool timing).
