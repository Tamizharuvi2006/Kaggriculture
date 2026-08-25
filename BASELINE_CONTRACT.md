# 🏛️ APEX PRODUCTION RELEASE CONTRACT & WORKFLOW

---

## 1. 🛡️ Immutable Production Rules

1. **Active Agent Immutability**:
   - Zero live hotfixes.
   - Zero live parameter tuning directly from individual match results.
   - Live telemetry is observational evidence, not direct feedback for immediate mutation.

2. **One Variable Family per Candidate**:
   - Experiments must isolate a single dimension:
     - 🌾 **Crop/Resource Allocation**
     - 🐄 **Livestock / Milk Timing**
     - 💰 **Inventory / Liquidity / Cash Buffers**
     - 🏷️ **Market Pricing & Order Execution**
     - 🧠 **Opponent Modeling / Anti-Exploit**
   - Compound multi-axis modifications are strictly forbidden on a single candidate branch.

3. **Hypothesis-Driven Engineering**:
   - Every candidate branch must state an explicit mechanism-level hypothesis:
     > *Mechanism $X$ causes failure in archetype $Y$; modifying $X \to X'$ improves MCV and win rate without destabilizing $Z$.*

4. **Frozen Holdout & Anti-Cherry-Picking Protocol**:
   - Evaluation seeds are deterministically generated and frozen (`HOLDOUT_SEEDS_V1`, $N \ge 100$).
   - **Single-Shot Evaluation**: A candidate is evaluated against the frozen holdout exactly once.
   - **Zero Post-Holdout Mutation**: If a candidate fails any gate, it is permanently marked **`FALSIFIED / REJECTED`**. No seed re-sampling, exclusion of hard seeds, or threshold tuning.

---

## 2. 📊 Enforceable Statistical Promotion Gates

A candidate must satisfy **all five** quantitative gates simultaneously on the frozen holdout suite:

| Metric | Required Condition | Statistical Verification | Failure Consequence |
| :--- | :--- | :--- | :--- |
| **Win Rate ($\text{WR}$)** | $\Delta \text{WR} \ge +2.5\%$ vs Baseline | Paired Wilcoxon / Binomial Test ($p < 0.05$) | Immediate Rejection |
| **Mean Wealth ($\mu_{\text{MCV}}$)** | $\mu_{\text{MCV}}(\text{Cand}) \ge \mu_{\text{MCV}}(\text{Base}) + 2{,}000$ | Paired Student's $t$-test ($p < 0.05$) | Immediate Rejection |
| **Variance / Volatility** | $\sigma_{\text{Cand}} / \sigma_{\text{Base}} \le 1.10$ | $F$-test for variance equality ($p > 0.05$) | Immediate Rejection |
| **5th Percentile Tail Risk** | $\text{MCV}_{p05}(\text{Cand}) \ge \text{MCV}_{p05}(\text{Base})$ | Non-parametric quantile bootstrap | Immediate Rejection |
| **PASS / Stall Volatility** | $\text{Rate}_{\text{PASS}}(\text{Cand}) \le \text{Rate}_{\text{PASS}}(\text{Base}) + 0.2\%$ | Max consecutive PASS turns $\le 3$ | Immediate Rejection |
| **Step Latency** | Mean $\le 20\text{ms}$, Max $\le 200\text{ms}$ | Hard timeout guarantee ($< 1.0\text{s}$) | Immediate Rejection |

---

## 3. 📋 Baseline Contract Snapshot: APEX 3.5 / 3.6

```yaml
baseline_id: "APEX-3.5-PROD"
submission_status: "ACTIVE_FROZEN"
freeze_timestamp: "2026-08-14T15:20:00Z"
lineage:
  parent: "APEX-3.4"
  architecture: "Fixed-Schedule Hybrid Planner with Bounded Liquidity Floor"
performance_profile:
  known_ladder_elo: "~1650-1700"
  benchmark_win_rate_vs_v41: "79.2%"
  mean_final_mcv: 142850
  p05_tail_mcv: 98400
  p95_peak_mcv: 189200
runtime_characteristics:
  avg_step_latency_ms: 12.4
  max_step_latency_ms: 85.0
  pass_action_rate: "0.8%"
known_failure_archetypes:
  - id: "ARCH-01"
    name: "Day 12 Liquidity Squeeze"
    description: "Aggressive cow purchase right before unexpected market slump causes crop planting delay."
  - id: "ARCH-02"
    name: "Late-Game Milk Bottleneck"
    description: "Worker contention between final harvesting and late milking window."
```

---

## 4. 📜 Immutable Experiment Audit Schema

Every local run that touches the frozen holdout must log a JSON entry to `reports/experiment_ledger.jsonl` matching this schema:

```json
{
  "experiment_id": "EXP-0112",
  "timestamp": "2026-08-14T15:21:00Z",
  "baseline_id": "APEX-3.5-PROD",
  "candidate_id": "CAND-0112-DYNAMIC-DISCARD",
  "variable_family": "Timing",
  "hypothesis": "Dynamic scheduler will adapt to market swings better than fixed schedule.",
  "code_hash": "c4b8e21a",
  "holdout_suite": "HOLDOUT_V1_N100",
  "evaluation_mode": "SINGLE_SHOT",
  "results": {
    "win_rate_delta": -0.792,
    "mean_mcv_delta": -85400,
    "tail_p05_delta": -98000,
    "pass_rate_delta": +0.885,
    "p_value": 0.0001
  },
  "gate_outcome": "FALSIFIED_REJECTED",
  "rejection_gate": "Gate 1 (Exact Replay) & Gate 4 (PASS Volatility Catastrophe)",
  "promoted_to_submission": false
}
```

---

## 5. 🧪 Candidate Validation Lifecycle

```
[ LIVE APEX 3.5 PROD ]
       │
Live Telemetry Ingestion
       ↓
Identify Failure Archetype
       ↓
Formulate Mechanism Hypothesis
       ↓
Create Isolated Candidate Branch
       ↓
Gate 1: Exact Loss Replay (ARCH-XX)  ────► [FAIL] ──► Audit Log (FALSIFIED) ──► Re-hypothesize
       ↓ [PASS]
Gate 2: Historical Loss Suite (N=50) ────► [FAIL] ──► Audit Log (FALSIFIED) ──► Re-hypothesize
       ↓ [PASS]
Gate 3: Frozen Blind Holdout (N≥100) ───► [FAIL] ──► Audit Log (FALSIFIED) ──► Re-hypothesize
       ↓ [PASS]
Gate 4: Statistical & Tail-Risk Gate ────► [FAIL] ──► Audit Log (FALSIFIED) ──► Re-hypothesize
       ↓ [ALL GATES PASSED]
Audit Log (PROMOTED)
       ↓
Single Kaggle Submission (APEX 3.6)
       ↓
Promoted to NEW FROZEN PRODUCTION
```
