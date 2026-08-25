# 🧪 EXP-0114 — HYPOTHESIS CARD (Second Research Cycle)

**Status**: FORMULATED — awaiting gate execution
**Parent**: EXP-0113 (FALSIFIED — Gate 1: 52.2% WR, ΔMCV +4.4, 46 real loss seeds)
**Origin**: EXP-0113 diagnostics (mechanism direction positive, activation too narrow)

---

## Evidence Chain (why this experiment exists)

1. **EXP-0113 falsification** (seat-balanced, 92 matches): the gentle-rebound gate fired in only **5/46 seeds** — it changed behavior too rarely to matter. ΔMCV +4.4, WR 52.2% < 60% floor.
2. **EXP-0113 direction evidence**: when the gate DID fire (5 seeds, 37 suppressed orders), win points were **7/10** — suppression of the collapsing product's sales is directionally correct.
3. **Order-path diagnostic** (8 loss seeds, 113 collapse agent-steps): the champion issues **60 STRAWBERRY + 32 MELON SELL orders during confirmed collapse windows** — 25% of its total strawberry sales happen inside collapses. Exit timing is a real, active mechanism, and the EXP-0113 gate was missing most of these events (its `drift ≤ −30% AND price < MA24` AND-condition is too narrow: the champion sells in the early crash phase before the trailing drift accumulates).
4. **Memory gate**: GENERATE — activation variant not previously attempted; EXP-0113 surfaced as prior.

---

## Hypothesis (single variable family: `Pricing`)

> **Mechanism**: Trend-filtered sell suppression. Suppress SELL orders of a decisive product (STRAWBERRY/MELON) while its price trades **below its 24-step moving average** — the regime-agnostic trend filter — and release sales when the price recovers at/above the MA. To bound the tail risk of holding through an extended bear market, suppression is **capped at 48 consecutive steps (6 days) per product**; beyond the cap the champion's natural sell logic resumes unconditionally.

**Why this differs from the falsified EXP-0113**: identical suppression action, but the trigger is the single dynamic condition `price < MA24` (no static threshold, no drift accumulation lag). It fires at the *start* of every decline, not only after a ≥30% 3-step crash has already accumulated. The 48-step cap is a new, pre-registered risk bound.

**Expected upside**: MCV_p05 +2,000+; WR +2.5% on the frozen holdout; suppression engages on the 60+ collapse-window SELLs the diagnostic proved exist.
**Expected downside (must be checked)**: holding into deeper crashes (tail risk) — bounded by the 48-step cap and p05 gate; cash starvation if suppression coincides with the champion's operating-reserve sales (PASS/latency unchanged — overlay never touches farmer actions).
**Named rival** (if EXP-0114 fails): the weakness is not sale timing at all — it is *re-entry* (rebuying / replanting into collapse-trough prices), which becomes EXP-0115.

---

## Candidate spec (Phase 4)

- **Variable family**: `Pricing` (same as parent, single change to activation rule)
- **Baseline**: `submission.py` (APEX 3.6 PROD, code_hash `f10bb5ea…`) — IMMUTABLE
- **Modification surface**: one overlay in the market-order path (identical to EXP-0113's wrapper, different gate)
- **Overlay parameters**: `MA_LOOKBACK=24`, `HOLD_CAP_STEPS=48`, decisive products STRAWBERRY/MELON

## Gates (Phase 5)

| Gate | Suite | Pass rule |
| :--- | :--- | :--- |
| 1. Exact Replay | 46 real loss seeds × 2 seats (apex33 cache) | ≥60% WR |
| 2. Historical Suite | 50 fixed seeds × 2 seats (10 groups × 5) | ≥75% overall, no group <60% |
| 3. Frozen Holdout | HOLDOUT_V1_N100, single shot | paired vs baseline |
| 4. Statistical Judge | 6 dimensions | ΔWR ≥ +2.5%, ΔMCV ≥ +2,000, σ ≤ 1.10, p05 ≥ base, added PASS ≤ 3, latency ≤ 20/200ms |

**Harness note**: all gates use the seat-balanced double-run (2 matches/seed) that EXP-0113's harness bug exposed; seat confounds are eliminated. A falsification is a good outcome — it yields EXP-0115 (re-entry hypothesis).
