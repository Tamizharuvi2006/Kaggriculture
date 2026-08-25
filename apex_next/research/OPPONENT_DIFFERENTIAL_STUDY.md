# 🧪 OPPONENT-DIFFERENTIAL STUDY — SUPPLY_COLLAPSE ATTRIBUTION (2026-08-14)

**Study id**: `OPP-DIFF-1` · **Status**: COMPLETE · **Production impact**: none (APEX frozen)
**Question**: Is APEX's ~46% SUPPLY_COLLAPSE WR an APEX-specific weakness, or shared
by the elite field? → Decide whether the regime thread deserves EXP-0117.

---

## Pre-registered decision rule

| Observation | Verdict | Action |
| :-- | :-- | :-- |
| APEX collapse WR ≈ elite reference WR (within ±5pp / ±1σ) | Regime NOT APEX-specific | Close SUPPLY_COLLAPSE thread; do NOT modify production for it |
| APEX collapse WR ≪ elite (≥10pp) AND non-collapse control clean | Regime IS APEX-specific | EXP-0117 (structural/production family) becomes justified |

---

## Leg A — Real telemetry (zero compute)

**Data**: 42 of 43 real APEX-lineage matches (refs 55373438 / 55373932 / 55376463) from
`mcv_replay_dataset.json`, joined with opponent Elo (`initialScore`) from the episode
exports; regime tagged per match from the shared market price series (3-sample drift
≤ −30% on STRAWBERRY/MELON — the fingerprint-calibrated definition). Controls: same
seed, same regime definition, same observation count, paired comparison.

Provenance note: the fingerprint dataset is ref **55373438**'s matches, not 55483322.

### Result — APEX WR by opponent tier (n=42 matches, 41 collapse-tagged)

| Opponent tier | SUPPLY_COLLAPSE | ALL matches (control) | Δ |
| :-- | --: | --: | --: |
| ELITE (top quartile, initialScore ≥ 1,161) | **25.0%** (3/12) | **34.2%** (27/79) | −9pp, Fisher p≈0.52 |
| TIER-2 (below 75th) | **79.3%** (23/29) | **53.9%** (125/232) | +25pp |
| APEX-stronger (score gap > 0) | 73.9% (17/23) | — | — |
| Opponent-stronger (gap < 0) | 50.0% (9/18) | — | — |
| Collapse duration (steps) | 10.9 (elite) vs 10.9 (tier-2) | — | identical |

**Read**: the market regime is identical across tiers (duration equal); only opponent
quality differs. APEX's collapse WR vs elite (25%) is statistically indistinguishable
from its OVERALL WR vs elite (34.2%) — the headline 46% was an opponent-mix artifact,
not a regime weakness. Collapse actually HELPS APEX vs weaker opponents (+25pp vs its
normal tier-2 WR): the regime is a variance amplifier that favors the stronger player.

## Leg B — Controlled local round-robin (360 matches, deterministic)

**Design**: 4 local agents × round-robin on 30 fresh seeds (master 20260814), seat-balanced
double-run per pair (2 matches/seed, seats swapped), shared regime tag from the market
series (identical for both sides). 100% of seeds collapse-tagged (full-match tag is
near-universal) → partitioned by severity (min_drift3 ≤ −0.60 = severe).

### Result — severe-collapse WR / MCV / p05 (n=90 per agent: 3 opponents × 30 seeds)

| Agent | WR% | MCV mean | p05 |
| :-- | --: | --: | --: |
| apex35 (vaulted 3.5) | **93.3** | 54,700 | 10,600 |
| v18 (original benchmark) | **73.3** | 55,219 | 10,768 |
| **APEX PROD (submission.py)** | **31.1** | 88,042 | 37,070 |
| v83 (experimental) | 2.2 | 90,188 | 47,701 |

Per-pair detail (30 seeds each): APEX vs apex35 = 0/30, APEX vs v18 = **0/30**
(87k vs 31k both seats), APEX vs v83 = 28/30, apex35 vs v18 = 28/30, apex35 vs v83 = 30/30,
v18 vs v83 = 30/30. Deterministic (byte-identical reruns; no seat splits on decisive pairs).

**Self-play sanity check (identical seeds, both seats)**:
| Seed | PROD | v18 | apex35 |
| --: | --: | --: | --: |
| 34083081 | 57,254 / 57,254 | 68,854 / 67,139 | 68,233 / 66,428 |
| 73332701 | 84,562 / 84,562 | 124,752 / 124,476 | 123,516 / 123,805 |

**Read**: the strength gap is AGGREGATE, not regime-specific. v18 and apex35 out-score
PROD on self-play on identical seeds; the round-robin hierarchy is apex35 > v18 > APEX > v83.
Because the collapse tag covers every seed, there is NO non-collapse control within Leg B —
the gap manifests in all matches, so it cannot be attributed to SUPPLY_COLLAPSE.

---

## Conclusion

1. **SUPPLY_COLLAPSE is NOT an APEX-specific weakness** (Leg A): collapse WR vs elite
   ≈ overall WR vs elite; the 46% headline was opponent-mix. **The regime thread closes.**
   **EXP-0117 (structural, SUPPLY_COLLAPSE-motivated) is NOT justified.**
2. **APEX's real problem is global strength, not regime**: locally, PROD is third of four
   (31.1% WR vs 73.3/93.3% for the reference frontier), and the vaulted apex35 (3.5)
   sweeps PROD (3.6) 30/30 — consistent with the live ladder (latest ref 46.4% < older
   ref 55.6%). Prior "79.2–88% WR vs V4.1/v18" claims were artifacts of the old
   single-match, seed%2 seat-confounded protocol (also flagged in Cycle 1).
3. Production remains frozen; no modifications made. Follow-up (deferred, requires user
   decision): verify the 3.5 → 3.6 regression on the seat-balanced harness and re-baseline
   the champion's true strength.

## Artifacts

- Leg A script + raw results: `apex_next/research/opponent_differential_legA.py`,
  `opponent_differential_legA_results.json`
- Leg B script + per-pair JSONs + summary: `apex_next/research/opponent_differential_legB.py`,
  `opponent_differential_legB_results/`
- Ledger record: `OPP-DIFF-1` (append-only)