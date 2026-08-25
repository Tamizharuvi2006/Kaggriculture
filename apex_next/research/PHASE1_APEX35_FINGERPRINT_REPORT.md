# 📊 PHASE 1 — APEX 3.5 EMPIRICAL FINGERPRINT (Research Cycle #1)

**Generated**: August 14, 2026 | **Generator**: `apex_next/research/phase1_apex35_fingerprint.py` | **Snapshot**: `apex_next/research/APEX35_FINGERPRINT.json`

> This is the **empirical baseline** of the current production agent. Every future experiment compares against these numbers. It does NOT claim the architecture improved Elo — it establishes what we are improving **from**.

---

## 1. Artifact Provenance (the agent being fingerprinted)

| Artifact | Hash |
| :--- | :--- |
| `submission.py` code (SHA-256) | `f10bb5ea10a34923…` |
| `DEFAULT_STRATEGY` config (canonical JSON) | `2c29716e6597448c…` |
| Documented APEX 3.5 candidate hash | `78738c1b` |

---

## 2. MCV / WR / Tail Distribution (86 real trajectories, `mcv_replay_dataset.json`)

| Metric | Value |
| :--- | :--- |
| Trajectories | 86 (43 matches × 2 players) |
| Win rate (dataset-wide) | 50.0% ⚠️ *dataset artifact — see caveat* |
| Mean MCV | 68,744 |
| Std MCV | 28,039 |
| Median MCV | 67,188 |
| p05 (tail risk) | 25,143 |
| p10 | 34,040 |
| p90 | 103,173 |
| p95 | 115,289 |

⚠️ **Caveat**: `won_match` is per-player, so a 2-player dataset always aggregates to ~50%. The **relative per-regime deltas are the signal**, not the aggregate.

---

## 3. Regime Performance Map (real data — calibrated detector)

| Regime | Matches | Win Rate | Mean MCV | p05 | Signal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SUPPLY_COLLAPSE** | 78 | **46.2%** 🔴 | 67,001 | 24,069 | Weakness |
| LIQUIDITY_SHOCK | 8 | 87.5% | 85,736 | 43,954 | Strength |

**Per-product breakdown of the weakness**: STRAWBERRY is the dominant collapse product — 55/86 trajectories, 47% WR there (26W/29L). MELON collapse: 21 trajectories. Confirms prior research: wealth deltas are price-realization driven, not physical-production driven.

---

## 4. Live Ladder Snapshot (807 real matches, 10 submissions)

| Submission ref | Identity | Matches | WR | Mean MCV | Seat0 WR | Seat1 WR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 55249106 | V4.1 Master (protected) | 215 | 23.7% | 112,479 | 23.0% | 24.4% |
| 55421857 | APEX 3.3 | 114 | 43.9% | 83,342 | 38.5% | 51.0% |
| 55411304 | APEX 3.0 | 101 | 41.6% | 79,938 | 39.2% | 44.0% |
| 55382689 | Competitive V13 | 82 | 45.1% | 74,607 | 43.3% | 46.2% |
| 55376463 | — | 66 | 47.0% | 76,279 | 47.2% | 46.7% |
| 55329352 | Monolithic submission | 64 | 45.3% | 60,573 | 37.8% | 55.6% |
| 55483322 | latest ref (APEX 3.5/3.6) | 56 | 46.4% | 81,953 | 50.0% | 44.4% |
| 55373932 | — | 48 | 62.5% | 86,245 | 65.6% | 56.3% |
| 55247715 | — | 34 | 50.0% | 14,284 | 57.9% | 40.0% |
| 55373438 | — | 27 | 55.6% | 65,112 | 64.3% | 46.2% |

⚠️ **Caveats**: (1) matches span different time windows — the live field got dramatically stronger (Elo inflation in `manifest.csv`: median 669 → 3,068 in 11 days); cross-ref WR comparisons are NOT apples-to-apples. (2) `55249106` (V4.1) shows 23.7% WR *today* because it plays the 2026-08-14 field, not its 2026-08-04 field.

---

## 5. Phase 2 — Priority Engine Verdict (real failure clusters)

| Archetype | Loss share | Impact (1−WR) | Confidence | Penalized Score |
| :--- | :--- | :--- | :--- | :--- |
| **SUPPLY_COLLAPSE** | 97.7% | 0.538 | 1.00 | **3.16** 🎯 |
| LIQUIDITY_SHOCK | 2.3% | 0.125 | 0.20 | 0.00 |

> **Selected weakness: `SUPPLY_COLLAPSE` — the champion loses when a decisive product (primarily STRAWBERRY) price collapses ≥30% over 3 steps. 78/86 real trajectories (91%) experience this regime; win rate there is 46.2%.**

This is the statistically supported, highest-value attack surface for the first challenger.

---

## 6. What This Fingerprint Does NOT Claim

- It does NOT claim the new lab architecture increased Elo.
- It does NOT replace the contract benchmarks (WR 79.2% vs V4.1, MCV 142,850 are *paired* holdout numbers; this fingerprint is *population* telemetry).
- It IS the frozen reference point for EXP-0113 onward.