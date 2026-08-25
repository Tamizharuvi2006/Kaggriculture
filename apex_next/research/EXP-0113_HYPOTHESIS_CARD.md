# 🧪 EXP-0113 — HYPOTHESIS CARD (First Contract-Compliant Research Cycle)

**Status**: FORMULATED — awaiting candidate build & gate execution
**Origin**: Phase 1 fingerprint + Phase 2 priority engine (real data, `APEX35_FINGERPRINT.json`)

---

## Evidence Chain (why this experiment exists)

1. **Regime detector (real 86 trajectories)**: `SUPPLY_COLLAPSE` = 78/86 trajectories (91%), win rate **46.2%** vs 87.5% in LIQUIDITY_SHOCK.
2. **Per-product attribution**: STRAWBERRY collapse drives the weakness (55/86 trajectories, 47% WR).
3. **Priority engine**: SUPPLY_COLLAPSE selected (score 3.16) — 97.7% of observed losses occur in this regime.
4. **Prior research alignment**: Phases 31–33 proved wealth deltas are 100% price-realization driven; Phase 67 showed clearance preemption dumps inventory into price crash troughs ($70–$90/u).
5. **Prior falsifications that constrain the mechanism (do not violate)**:
   - Phase 75–76: static price thresholds → falsified (+$4.92 price, −$119 wealth, 38% WR). **No static thresholds.**
   - Phase 80–81: static batch capping → falsified (free-rider trap, 12% WR). **No unilateral holding without opponent context.**
   - Phase 107: dynamic scheduler → falsified (0% WR, 2,200+ PASS turns). **No full-engine rearchitecture; overlay only, fixed schedule intact.**

---

## Hypothesis (single variable family: `Pricing`)

> **Mechanism**: During a confirmed `SUPPLY_COLLAPSE` regime of a decisive product (STRAWBERRY/MELON price dropping ≥30% over 3 steps), the champion's exit policy realizes sales into the collapse trough. Overlaying a **regime-gated gentle-rebound exit** — suppress non-essential SELL of the collapsing product until (a) the 3-step drift turns positive **or** (b) the product's price recovers above its 24-step moving average — improves mean MCV and p05 tail without increasing PASS turns.

**Why this differs from the falsified attempts**: it is (a) regime-conditional (fires only on real collapse evidence), (b) inventory-preserving rather than batch-capping (sales are delayed, not split), and (c) a pure market-timing overlay — the fixed v18 production schedule, worker scheduler, and opening are untouched.

**Expected upside**: MCV_p05 +2,000+ in collapse regimes; overall WR +2.5% on the frozen holdout.
**Expected downside (must be checked)**: delayed strawberry/melon exits risk holding into a deeper crash (tail risk) and could raise PASS/turn count during the hold window (≤3 max consecutive PASS gate).
**Known rival hypothesis** (honest alternative): collapse-phase losses are seat-1 asymmetries (Phase 105), not exit timing — if the exit overlay fails Gate 1, the seat-conditioned variant becomes EXP-0114.

---

## Candidate spec (Phase 4 — build ONE)

- **Variable family**: `Pricing`
- **Baseline**: `submission.py` (APEX 3.6 PROD, code_hash `f10bb5ea…`)
- **Modification surface**: one gated overlay in the market-order construction path only.
- **Explicitly untouched**: opening, fixed schedule, worker scheduler, animal plans, hysteresis gates, v17/v18 ranker internals.

---

## Gates (Phase 5 — kill it aggressively)

| Gate | Suite | Pass rule |
| :--- | :--- | :--- |
| 1. Exact Replay | motivating loss seeds (SUPPLY_COLLAPSE losses) | ≥60% WR |
| 2. Historical Suite | 50 multi-archetype seeds | ≥75% overall, none <60% |
| 3. Frozen Holdout | `HOLDOUT_V1_N100` | single shot, paired vs baseline |
| 4. Statistical Judge | 6 dimensions | ΔWR ≥ +2.5%, ΔMCV ≥ +2,000, σ ≤ 1.10, p05 ≥ base, PASS ≤ 3, latency ≤ 20/200ms |

**Falsification is a good outcome**: a failed Gate 1/2/3 produces an immutable ledger record proving exit-timing is not the mechanism — that knowledge feeds EXP-0114.

---

## Execution order (by the orchestrator)

1. `ExperimentMemory.search_hypothesis` — confirm no falsified prior on this exact mechanism (memory gate).
2. `CandidateBuilder.create_candidate_branch` — `experiments/EXP-0113/` + SHA-256.
3. `ExactReplayEngine` → `HistoricalSuiteEngine` → `FrozenHoldoutEngine` → `StatisticalJudge`.
4. `AuditLedger.append_record` — with provenance, regime tags `["SUPPLY_COLLAPSE","STRAWBERRY"]`, priority score, population metrics.
5. On PASS: `ReleaseManager.prepare_release` → `ChampionRegistry.promote_challenger` → `RegressionSentinel` armed with fingerprint expectations.