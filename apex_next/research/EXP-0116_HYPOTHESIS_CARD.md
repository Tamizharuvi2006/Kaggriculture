# 🧪 EXP-0116 — HYPOTHESIS CARD (Fourth Research Cycle)

**Status**: FORMULATED — awaiting gate execution
**Parent**: EXP-0115 (FALSIFIED — re-entry deferral inert, fires 2/46 seeds)
**Origin**: Sell-path diagnostic — the champion liquidates its cash engine into collapse windows

---

## Evidence Chain (why this experiment exists)

1. **Falsification stack on SUPPLY_COLLAPSE order timing**:
   - EXP-0113 (drift ∧ below-MA sell gate): inert — 5/46 seeds, 52.2% WR.
   - EXP-0114 (below-MA sell gate): catastrophic — 45/46 seeds, 6.5% WR, ΔMCV −8,126.
   - EXP-0115 (seed-buy deferral): inert — 2/46 seeds, 52.2% WR.
2. **Sell-path diagnostic** (8 loss seeds, 122 collapse agent-steps ≈ 1% of steps): the champion's collapse-window SELL mix is dominated by its **daily revenue engine**, not the collapsing crop:
   - MILK: **66 sells during collapse** (16% of all milk sells in ~1% of steps → ~16× over-represented)
   - WOOL: 44 sells (16% of 278)
   - STRAWBERRY: 60, MELON: 32 (the collapsing products themselves)
3. The champion **liquidates milk/wool into the crash** — the cash raised funds re-entry at trough prices (the EXP-0115 buys). If the sell-side of that rotation is the loss mechanism, deferring the cash-engine sales during the collapse window is the last untested order-level variant.

---

## Hypothesis (single variable family: `Pricing`)

> **Mechanism**: Cash-engine hold. While a decisive product (STRAWBERRY/MELON) is in a confirmed SUPPLY_COLLAPSE (3-step drift ≤ −30%, the fingerprint-calibrated threshold), suppress **SELL orders of MILK and WOOL** — the champion's daily revenue stream — holding the inventory until the 3-step drift of the decisive product turns ≥ 0 (recovery) or a hard cap of **24 steps** (1 day). All other orders and farmer actions untouched.

**Why this differs from the falsified parents**:
- vs EXP-0113/0115 (inert): the affected orders are MILK/WOOL — present in the champion's market orders EVERY step, so the overlay fires whenever a collapse window is active (the diagnostic proves 66+44 such events); it cannot be structurally inert.
- vs EXP-0114 (harmful): the trigger is the calibrated collapse regime (~1% of steps), NOT the below-MA filter that fired 45/46 seeds and starved cash for entire matches. Exposure is bounded to collapse windows + a 24-step cap.
- Risk acknowledged: deferring milk/wool sales may starve operating cash DURING the window — that is exactly the hypothesis under test (does holding the cash engine through the crash beat liquidating into it?).

**Expected upside**: preserve revenue for the post-collapse recovery wave; WR +2.5%, MCV +2,000 on the frozen holdout.
**Expected downside (must be checked)**: cash shortfall during holds (p05 gate); missed milk-sale windows if the recovery lags the cap (bounded by 24 steps).
**Named rival** (final in this family): if EXP-0116 fails, the order layer is exhausted — the SUPPLY_COLLAPSE weakness is structural (farm-plan / production family), which becomes EXP-0117.

---

## Candidate spec (Phase 4)

- **Variable family**: `Pricing` (sell timing; last order-level variant)
- **Baseline**: `submission.py` (APEX 3.6 PROD, code_hash `f10bb5ea…`) — IMMUTABLE
- **Modification surface**: one market-order filter (drop SELL:MILK / SELL:WOOL during active collapse); wrapper identical in structure to EXP-0113–0115 candidates
- **Parameters**: `COLLAPSE_DRIFT = −0.30`, `REARM_DRIFT = 0.0`, `HOLD_CAP_STEPS = 24`, decisive products STRAWBERRY/MELON, held products MILK/WOOL

## Gates (Phase 5)

| Gate | Suite | Pass rule |
| :--- | :--- | :--- |
| 1. Exact Replay | 46 real loss seeds × 2 seats | ≥60% WR |
| 2. Historical Suite | 50 fixed seeds × 2 seats (10 groups × 5) | ≥75% overall, no group <60% |
| 3. Frozen Holdout | HOLDOUT_V1_N100, single shot | paired vs baseline |
| 4. Statistical Judge | 6 dimensions | ΔWR ≥ +2.5%, ΔMCV ≥ +2,000, σ ≤ 1.10, p05 ≥ base, added PASS ≤ 3, latency ≤ 20/200ms |

**Harness**: seat-balanced double-run; determinism verified (byte-identical reruns); candidate_path passed explicitly (EXP-0115 harness bug fixed and corrected in the ledger).