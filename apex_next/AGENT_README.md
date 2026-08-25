# 🤖 APEX NEXT — Self-Improving Kaggriculture Research Agent (Full System Spec)

> **Path**: `D:\Kaggriculture\apex_next\`
> **Purpose**: This document is the **complete implementation spec** of the apex_next research agent. It describes every module, every public interface, every data schema, and every workflow so that any other agent (human or LLM) can read, extend, or operate this system without re-deriving it from code.
> **Live Champion**: `D:\Kaggriculture\submission.py` (APEX 3.6 PROD — frozen, immutable, on Kaggle)
> **Contract**: `D:\Kaggriculture\BASELINE_CONTRACT.md`

---

## 1. What apex_next Is

apex_next is a **deterministic, memory-guided autonomous research lab** that improves the Kaggriculture tournament agent without ever touching the frozen live submission directly.

- 🧠 **AI proposes** hypotheses
- 🧪 **Experiments measure** them against frozen benchmarks
- 📊 **Statistics judge** promotion
- 📜 **Contracts protect** the live agent
- 🚀 **Release controller deploys** (and only it may write `submission.py`)

The system converts live telemetry into failure clusters, ranks them by expected value, checks research memory to avoid repeating falsified dead ends, builds an isolated candidate, runs it through a 4-gate falsification gauntlet, and — only if every gate passes — hands the candidate to the release manager and registers it as the new champion.

---

## 2. Folder Layout

```
apex_next/
├── AGENT_README.md          ← this file (full spec)
├── gpu_engine/              ← ⚡ accelerated batch simulation engine (RTX 4050 / Vectorized)
│   ├── README.md                # engine spec & parity contract
│   ├── python_ref_engine.py     # fast Python in-memory reference simulator
│   ├── differential_tester.py   # golden trajectory comparator against kaggle_environments
│   ├── cuda_batch_engine.py     # vectorized parallel simulator (32..256 envs)
│   └── benchmark_throughput.py  # progressive scaling throughput benchmark
└── lab/                     ← the 17-module agent package
    ├── __init__.py
    ├── orchestrator.py          # wires ALL 17 stages
    ├── telemetry_ingestor.py    # 1. read-only real-data ingestion
    ├── diagnostics_analyzer.py  # 2. failure archetype classification
    ├── hypothesis_generator.py  # 3. single-variable hypothesis spec
    ├── candidate_builder.py     # 4. isolated EXP-XXXX branch + SHA-256
    ├── exact_replay_engine.py   # 5. Gate 1: exact loss replay
    ├── historical_suite_engine.py # 6. Gate 2: 50-seed regression suite
    ├── frozen_holdout_engine.py # 7. Gate 3: HOLDOUT_V1_N100 single-shot
    ├── statistical_judge.py     # 8. Gate 4: 6-dimension contract check
    ├── audit_ledger.py          # 9. append-only JSONL provenance ledger
    ├── release_manager.py       # 10. sole write authority over submission.py
    ├── experiment_memory.py     # 11. hypothesis memory + genealogy  (NEW)
    ├── priority_engine.py       # 12. Impact×Freq×Conf×Fixability     (NEW)
    ├── regime_detector.py       # 13. market regime classification     (NEW)
    ├── artifact_hasher.py       # 14. SHA-256 provenance bundle        (NEW)
    ├── regression_sentinel.py   # 15. NORMAL→…→FREEZE live watch       (NEW)
    └── champion_registry.py     # 16. 🏆/🥊 promotion bookkeeping       (NEW)
```

Shared data (outside apex_next, at `D:\Kaggriculture\`):
- `reports/experiment_ledger.jsonl` — the append-only experiment memory
- `reports/champion_registry.json` — current champion record
- `reports/live_match_telemetry/submission_*_episodes.json` — real Kaggle episode exports (807 live matches)
- `mcv_replay_dataset.json` — real per-step replay dataset (5,160 rows / 86 trajectories)
- `experiments/EXP-XXXX/` — isolated candidate branches
- `submission.py` — the live champion (release manager's write target)

---

## 3. The 16-Stage Pipeline (End to End)

```
LIVE CHAMPION ──telemetry──► 1. TELEMETRY INGESTOR (read-only)
        ▼
2. DIAGNOSTICS ANALYZER  → failure archetypes per loss
        ▼
3. PRIORITY ENGINE       → Impact × Frequency × Confidence × Fixability
        ▼
4. HYPOTHESIS MEMORY     → LEARN (blocked, already falsified) | GENERATE (proceed)
        ▼
5. GENEALOGY ASSIGNMENT  → parent_exp_id from same family/archetype
        ▼
6. HYPOTHESIS GENERATOR  → immutable EXP-XXXX spec
        ▼
7. CANDIDATE BUILDER     → experiments/EXP-XXXX/ + SHA-256
        ▼
8. GATE 1 EXACT REPLAY   → motivates loss seeds (≥60% WR)
        ▼ PASS            (FAIL → audit FALSIFIED_GATE_1 → stop)
9. GATE 2 HISTORICAL     → 50 multi-archetype seeds (≥75% overall, none <60%)
        ▼ PASS            (FAIL → audit FALSIFIED_GATE_2 → stop)
10. GATE 3 FROZEN HOLDOUT → HOLDOUT_V1_N100, SINGLE_SHOT
        ▼
11. GATE 4 STATISTICAL   → 6-dimension contract (ΔWR≥+2.5%, ΔMCV≥+2000, σ≤1.10, p05, PASS, latency)
        ▼ PASS            (FAIL → audit FALSIFIED_REJECTED → stop)
12. RELEASE MANAGER       → validates AST, archives old, deploys submission.py
        ▼
13. CHAMPION REGISTRY    → promotes challenger → champion (only after confirmed deploy)
        ▼
14. REGRESSION SENTINEL  → watches first 20 live matches (NORMAL/SUSPICIOUS/REGRESSION/FREEZE)
        ▼
15. AUDIT LEDGER          → provenance + genealogy + regime + population metrics (immutable)
```

One experiment = one run of `LabOrchestrator.run_experiment_pipeline()`.

---

## 4. Module-by-Module Interface Spec

### 4.1 TelemetryIngestor — `lab/telemetry_ingestor.py`
Read-only. Parses the REAL Kaggle episode export format.

```
class TelemetryIngestor(logs_dir="reports/live_match_telemetry")
  parse_match_log(filepath)                          → dict telemetry | None
  parse_kaggle_episodes(filepath, our_submission_id=None) → list[telemetry]
  ingest_recent_matches(limit=50)                    → list[telemetry]
  ingest_live_telemetry(telemetry_dir=None)          → list[telemetry] (all submission_*_episodes.json)
```

**Kaggle episode schema parsed** (`reports/live_match_telemetry/submission_*.json`):
```json
{"submission": {"ref": 55421857, "publicScoreNullable": "1105.3", ...},
 "episodes": [{"id": 92857123, "state": "COMPLETED", "type": "EPISODE_TYPE_PUBLIC",
   "agents": [{"submissionId": 55421857, "reward": 118721, "index": 0,
               "initialScore": 1102.3, "updatedScore": 1105.4, ...}, ...]}]}
```

**Normalized telemetry dict** (both parsers):
```json
{"match_id": str, "filepath": str, "result": "WIN"|"LOSS"|"TIE",
 "our_mcv": float, "opp_mcv": float, "mcv_diff": float, "seat": int,
 "pass_turns": int, "pass_ratio": float, "total_steps": int,
 "actions_summary": {}, "market_events": [],
 "our_elo_delta": float,          // kaggle episodes only
 "opponent_submission_id": int,   // kaggle episodes only
 "raw_metadata": {episode_id, create_time, end_time, type, our_agent_id}}
```

**Verified against real data**: 807 live matches ingested (328 W / 479 L).

### 4.2 DiagnosticsAnalyzer — `lab/diagnostics_analyzer.py`
Maps losses to failure archetypes with an evidence chain.

```
ARCHETYPES = ["LIQUIDITY_SHOCK", "LATE_MILK_TIMING", "CROP_DRIFT",
              "PRICE_SPIKE", "OPPONENT_PREEMPTION", "SEAT_ASYMMETRY", "PASS_TURN_STALL"]

class DiagnosticsAnalyzer()
  diagnose_loss(telemetry)                    → {"status":"DIAGNOSED", "primary_archetype",
                                                  "secondary_archetypes", "mcv_deficit",
                                                  "evidence_chain": [str], "motivating_seed"}
  aggregate_failure_modes(telemetry_list)     → {"total_losses_analyzed", "archetype_frequencies",
                                                  "top_bottleneck", "diagnoses"}
```

Rules: PASS ratio >5% → PASS_TURN_STALL; seat==1 with >15k deficit → SEAT_ASYMMETRY; milk revenue <70% of opponent → LATE_MILK_TIMING; min cash <50 → LIQUIDITY_SHOCK; else CROP_DRIFT fallback.

### 4.3 HypothesisGenerator — `lab/hypothesis_generator.py`
Enforces one-variable-family hypothesis formulation.

```
VARIABLE_FAMILIES = ["Pricing", "Inventory_Liquidity", "Timing",
                     "Opponent_Adaptation", "Resource_Allocation"]
ARCHETYPE_TO_FAMILY = {LIQUIDITY_SHOCK→Inventory_Liquidity, LATE_MILK_TIMING→Timing,
                       CROP_DRIFT→Resource_Allocation, PRICE_SPIKE→Pricing,
                       OPPONENT_PREEMPTION→Opponent_Adaptation, SEAT_ASYMMETRY→Resource_Allocation,
                       PASS_TURN_STALL→Timing}

class HypothesisGenerator()
  generate_hypothesis(diagnostic_package, proposed_mechanism, variable_family=None)
      → {"experiment_id": "EXP-<MMDDHHMM>", "created_at", "target_archetype",
         "variable_family", "motivating_match_id", "motivating_seed",
         "evidence_summary", "mechanism_hypothesis", "expected_impact", "status": "FORMULATED"}
```

### 4.4 CandidateBuilder — `lab/candidate_builder.py`
```
class CandidateBuilder(base_experiments_dir="experiments")
  calculate_sha256(filepath) → hex str
  create_candidate_branch(hypothesis_spec, baseline_file, candidate_code_content, config=None)
      → {"experiment_id", "baseline_source", "baseline_hash", "candidate_file",
         "candidate_hash", "hypothesis", "config", "status": "BUILT"}
```
Writes `experiments/EXP-XXXX/candidate_agent.py`, `metadata.json`, `hypothesis.md`.

### 4.5 ExactReplayEngine — `lab/exact_replay_engine.py` (Gate 1)
```
class ExactReplayEngine(run_match_fn=None)
  run_exact_replay(candidate_meta, motivating_seeds, baseline_agent_fn=None, candidate_agent_fn=None)
      → {"gate": "GATE_1_EXACT_REPLAY", "passed": bool, "motivating_seeds_count",
         "wins", "win_rate", "avg_mcv_diff", "details": [{seed, win, mcv_diff}],
         "status": "PASS"|"FALSIFIED_GATE_1"}
```
Rule: win_rate ≥ 0.60. Default canary seeds if none given: `[42, 107, 504110]`.

### 4.6 HistoricalSuiteEngine — `lab/historical_suite_engine.py` (Gate 2)
```
HISTORICAL_ARCHETYPE_SEEDS = {archetype: [10 seeds]}  # 50 seeds total, 5 archetypes

class HistoricalSuiteEngine(run_match_fn=None)
  run_suite(candidate_meta, candidate_agent_fn=None)
      → {"gate": "GATE_2_HISTORICAL_SUITE", "passed": bool, "total_matches", "total_wins",
         "overall_win_rate", "archetype_breakdown": {archetype: {matches, wins, win_rate}},
         "status": "PASS"|"FALSIFIED_GATE_2"}
```
Rule: overall ≥ 0.75 AND no archetype below 0.60.

### 4.7 FrozenHoldoutEngine — `lab/frozen_holdout_engine.py` (Gate 3)
```
HOLDOUT_SUITE_VERSION = "HOLDOUT_V1_N100"
FROZEN_SEEDS_N100 = [1000 + i*37 + (i**2) % 997 for i in range(100)]   # deterministic & immutable

class FrozenHoldoutEngine(run_paired_match_fn=None)
  run_holdout(candidate_meta, baseline_agent_fn=None, candidate_agent_fn=None)
      → {"gate": "GATE_3_FROZEN_HOLDOUT", "holdout_suite", "total_matches", "candidate_wins",
         "candidate_losses", "ties", "win_rate", "baseline_mean_mcv", "candidate_mean_mcv",
         "baseline_std_mcv", "candidate_std_mcv", "baseline_p05_mcv", "candidate_p05_mcv",
         "avg_pass_turns", "max_pass_turns", "avg_latency_ms", "max_latency_ms"}
```
Single-shot: the candidate sees the suite exactly once.

### 4.8 StatisticalJudge — `lab/statistical_judge.py` (Gate 4)
```
class StatisticalJudge(min_wr_delta=0.025, min_mcv_delta=2000.0, max_variance_ratio=1.10,
                       max_pass_rate_delta=0.002, max_allowed_consecutive_pass=3,
                       max_mean_latency_ms=20.0, max_peak_latency_ms=200.0)
  evaluate(holdout_metrics, baseline_wr=0.50)
      → {"gate": "GATE_4_STATISTICAL_JUDGE", "promotable": bool,
         "verdict": "APPROVED_FOR_RELEASE"|"FALSIFIED_REJECTED",
         "criteria_checks": {win_rate_pass, mean_mcv_pass, variance_pass,
                             tail_risk_pass, pass_volatility_pass, latency_pass},
         "metrics": {wr_delta, mcv_delta, std_ratio, tail_p05_delta,
                     max_pass_turns, avg_latency_ms, max_latency_ms},
         "failed_reasons": [str]}
```
Requires ALL SIX dimensions simultaneously. No partial credit.

### 4.9 AuditLedger — `lab/audit_ledger.py`
Append-only JSONL. Every record is one immutable experiment lifecycle.

```
class AuditLedger(ledger_filepath="reports/experiment_ledger.jsonl")
  append_record(experiment_id, baseline_id, candidate_meta, hypothesis_spec,
                exact_replay_res, historical_res, holdout_res, judge_verdict,
                promoted=False, parent_exp_id=None, provenance=None,
                regime_tags=None, priority_score=None, population_metrics=None)
      → the record dict, appended atomically
```

**Record schema** (superset of the contract's audit schema):
```json
{"experiment_id": "EXP-0112", "timestamp": "…Z", "baseline_id": "APEX-3.5-PROD",
 "candidate_file": "experiments/EXP-0112/candidate_agent.py", "candidate_hash": "sha256",
 "variable_family": "Timing", "target_archetype": "CROP_DRIFT",
 "hypothesis": "…", "parent_exp_id": "EXP-0111", "gate_outcome": "…",
 "holdout_suite": "HOLDOUT_V1_N100", "evaluation_mode": "SINGLE_SHOT",
 "results": {win_rate_delta, mean_mcv_delta, tail_p05_delta, std_ratio, max_pass_turns},
 "gate_outcomes": {gate_1..gate_4},
 "failed_reasons": [], "promoted_to_submission": false,
 "provenance": {code_hash, baseline_hash, config_hash, holdout_hash, result_hash},
 "regime_tags": ["SUPPLY_COLLAPSE", "STRAWBERRY"],
 "priority_score": 1.24,
 "population_metrics": {win_rate, baseline_mean_mcv, candidate_mean_mcv, …}}
```

### 4.10 ReleaseManager — `lab/release_manager.py`
The ONLY component allowed to write `submission.py`.

```
class ReleaseManager(submission_target="submission.py", archive_dir="baseline/archive")
  validate_code_syntax(code_filepath) → bool   # AST parse
  prepare_release(candidate_meta, judge_verdict, new_version_tag="APEX-3.6-PROD")
      → {"status": "RELEASE_READY"|"REJECTED"|"FAILED", "version_tag",
         "submission_path", "candidate_hash", "timestamp"}
```
Sequence: reject if judge not promotable → reject if candidate file missing → reject if syntax fails → archive current submission.py → copy candidate in.

### 4.11 ExperimentMemory — `lab/experiment_memory.py` 🧠 (NEW)
Research memory: answers "have we already tried this?" and reconstructs lineage trees.

```
class ExperimentMemory(ledger_filepath="reports/experiment_ledger.jsonl")
  load_records()                    → list[record]
  search_hypothesis(variable_family=None, target_archetype=None,
                    mechanism=None, top_k=5)
      → {"verdict": "LEARN"|"GENERATE", "prior_attempts": [
           {experiment_id, score, match_reasons, gate_outcome,
            promoted_to_submission, hypothesis, results}], "reasons": [str]}
  assign_parent(variable_family, target_archetype=None) → parent_exp_id | None
  genealogy_tree()                  → {"total_experiments", "roots", "nodes",
                                       "lineages": [ASCII tree strings]}
  lineage_of(experiment_id)         → [ancestor chain, oldest first]
  attempt_count_for_archetype(target_archetype=None, variable_family=None) → int
```

**LEARN rule**: a prior attempt with similarity score ≥ 4.0 AND falsified AND not promoted blocks the new experiment (`verdict=LEARN`). Similarity = family match (+2), archetype match (+2), mechanism token overlap (+0.75/token, cap 3).

### 4.12 PriorityEngine — `lab/priority_engine.py` 🎯 (NEW)
```
class PriorityEngine()
  score_archetype(archetype, frequency, impact, confidence=0.5, fixability=0.5)
      → {archetype, frequency, impact, confidence, fixability,
         priority_score: 0..10}
  rank_clusters(clusters, attempt_penalty=None)
      → {"ranking": [scored], "selected_archetype", "selected_priority", "total_clusters"}
  select_next_experiment(diagnostics_aggregate, attempt_penalty=None, …)
      → wraps DiagnosticsAnalyzer.aggregate_failure_modes() output
```

- Priority = impact × frequency × confidence × fixability × 10
- Falsification penalty: `penalized = priority × 0.75^prior_attempts` — repeatedly attacked archetypes sink in rank, forcing exploration.

### 4.13 RegimeDetector — `lab/regime_detector.py` 🌊 (NEW)
Classifies real match economies; calibrated on the real 86-trajectory dataset.

```
REGIMES = ["STABLE", "INFLATION", "LIQUIDITY_SHOCK", "DEMAND_SPIKE",
           "SUPPLY_COLLAPSE", "OPPONENT_PRESSURE"]
DECISIVE_PRODUCTS = ("MILK", "WOOL", "STRAWBERRY", "MELON", "TOMATO", "CARROT", "WHEAT")

class RegimeDetector()
  classify_series(price_series, cash_series=None)
      → {"regime", "evidence": {...}, "reason"}
  classify_trajectory(trajectory_rows)
      → {"regime", "product", "evidence", "reason", "per_product": {product: regime}}
  evaluate_by_regime(dataset_rows)
      → {"total_trajectories", "by_regime": {regime: {matches, win_rate, mean_mcv, p05_mcv}},
         "classified", "weakest_regime", "weakest_win_rate", "diagnosis"}
  load_real_dataset(dataset_path="mcv_replay_dataset.json") → rows
```

**Classification order** (severity): LIQUIDITY_SHOCK (5) > DEMAND_SPIKE/SUPPLY_COLLAPSE (4) > OPPONENT_PRESSURE (3) > INFLATION (2) > STABLE (1).

**Calibration notes (IMPORTANT — do not revert)**: zero cash is the NORM for this reinvestment strategy (median min-cash $10 in the real population), so LIQUIDITY_SHOCK requires **cash == $0 AND a simultaneous 3-step price collapse ≤ −15%**. SUPPLE_COLLAPSE = 3-step cumulative drift ≤ −30%. INFLATION = window drift ≥ +20%. OPPONENT_PRESSURE = single-step move ≥ 8% without direction.

**Real-data result (verified)**: 86 trajectories → SUPPLY_COLLAPSE 78 matches @ 46% WR (STRAWBERRY-driven, 55/86) ← the agent's real weakness; LIQUIDITY_SHOCK 8 matches @ 87.5% WR.

### 4.14 ArtifactHasher — `lab/artifact_hasher.py` 🔐 (NEW)
```
class ArtifactHasher()
  hash_file(filepath) / hash_bytes(b) / hash_text(s) → hex
  hash_config(config)     # canonical sorted-key JSON
  hash_seed_list(seeds)   # sorted, comma-joined
  hash_metrics(metrics)   # canonical sorted-key JSON
  build_provenance(candidate_file, baseline_file, config, holdout_seeds, results)
      → {code_hash, baseline_hash, config_hash, holdout_hash, result_hash}
```

### 4.15 RegressionSentinel — `lab/regression_sentinel.py` 🛡️ (NEW)
```
class RegressionSentinel(expected_wr, expected_mean_mcv, expected_std_mcv,
                         min_sample_size=20, wr_emergency_delta=-0.15,
                         mcv_emergency_delta=-12000.0, suspicious_z=1.5,
                         regression_streak=3)
  observe(result, our_mcv)   # feed one live match (WIN/LOSS + MCV)
  evaluate() → {"state", "matches_observed", "min_sample_size", "live_wr",
                "live_mean_mcv", "wr_delta", "mcv_delta", "z_score",
                "emergency_breached", "recommendation", "note"}
```

**State machine** (deterministic):
- `n < min_sample_size` (20): emergency breach → SUSPICIOUS, else NORMAL. **No reversion decision ever below min sample.**
- `n ≥ 20` + emergency breach (WR ≤ expected−15% OR MCV ≤ expected−12,000) → **REGRESSION**, recommendation `FREEZE_AND_EVALUATE_FALLBACK`
- Else z-score ≤ −1.5 → SUSPICIOUS; else NORMAL

The sentinel **recommends**; the release controller decides. No auto-revert.

### 4.16 ChampionRegistry — `lab/champion_registry.py` 🥊 (NEW)
```
class ChampionRegistry(registry_filepath="reports/champion_registry.json")
  current_champion() → champion dict | None
  promote_challenger(challenger_meta, judge_verdict, holdout_res,
                     version_tag, release_confirmed=False)
      → {"status": "REJECTED"|"PENDING_DEPLOYMENT"|"PROMOTED", "champion"}
```

Promotion requires BOTH `judge_verdict["promotable"]` AND `release_confirmed=True` (set only after ReleaseManager confirms deployment). The registry is bookkeeping only — it never initiates a write.

### 4.17 LabOrchestrator — `lab/orchestrator.py`
The single entry point for the whole pipeline.

```
class LabOrchestrator(baseline_id="APEX-3.5-PROD")
  run_experiment_pipeline(diagnostic_package, proposed_mechanism, variable_family,
                          candidate_code_content, baseline_file="submission.py",
                          auto_promote=False, new_version_tag="APEX-3.6-PROD")
      → {"experiment_id", "verdict", "promoted", "metrics"}
        verdict ∈ {FALSIFIED_GATE_1, FALSIFIED_GATE_2, FALSIFIED_REJECTED,
                   APPROVED_FOR_RELEASE, BLOCKED_BY_MEMORY, NO_FAILURES_TO_ATTACK}
  watch_live_performance(expected_wr, expected_mean_mcv, expected_std_mcv, live_matches)
      → RegressionSentinel verdict
```

**diagnostic_package** (accepted keys):
```json
{"match_id": "ep-90744327", "primary_archetype": "LIQUIDITY_SHOCK",
 "motivating_seed": 504110, "evidence_chain": ["…"],
 "market_events": [prices...],          // optional flat price series
 "trajectory_rows": [replay rows...]}   // optional REAL trajectory → used for regime tags
```

Note: the orchestrator inserts `apex_next/` onto `sys.path` itself, so it runs from ANY working directory.

---

## 5. Data Contracts & Invariants (NON-NEGOTIABLE)

1. **Active immutability**: zero live hotfixes; telemetry is observational evidence only.
2. **One variable family per candidate** — compound multi-axis modifications are forbidden.
3. **Hypothesis-driven**: every candidate states a mechanism-level hypothesis.
4. **Single-shot frozen holdout**: `HOLDOUT_V1_N100`, evaluated exactly once; no seed re-sampling, no threshold tuning, no exclusion.
5. **Deterministic judge**: promotion is decided by code, never by LLM opinion.
6. **Append-only ledger**: records are never edited or deleted; `parent_exp_id` chains build the genealogy.
7. **Provenance**: every record carries code/baseline/config/holdout/result hashes.
8. **Monolithic packaging**: candidates are 100% self-contained single-file Python (`submission.py`-compatible).
9. **Write separation**: only `ReleaseManager` writes `submission.py`; only `ChampionRegistry` (after confirmed deploy) records the champion; only `AuditLedger` appends to the ledger.
10. **No auto-revert**: RegressionSentinel recommends; release controller decides.

---

## 6. How to Run (Verified Commands)

Python interpreter in this environment: `C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe`

```bash
# From the project root D:\Kaggriculture (paths are relative to the root):

# Real-data regime map (86 trajectories, mcv_replay_dataset.json)
python apex_next\lab\regime_detector.py

# Real live-match ingestion (807 matches from reports/live_match_telemetry/)
python apex_next\lab\telemetry_ingestor.py

# Experiment memory on the real ledger
python apex_next\lab\experiment_memory.py

# Full pipeline orchestration (memory gate + gates 1-4 + registry)
python -c "import sys; sys.path.insert(0, '.'); from apex_next.lab.orchestrator import LabOrchestrator; o = LabOrchestrator(); print(o.champion_registry.current_champion())"
```

Each module has a `__main__` self-test.

**Verified outputs (real data, August 14 2026)**:
- Telemetry: 807 live matches (328 W / 479 L)
- Regimes: SUPPLY_COLLAPSE 78 @ 46% WR ← weakest; LIQUIDITY_SHOCK 8 @ 87.5% WR
- Ledger: 1 record (EXP-8140956, APPROVED_FOR_RELEASE)
- Champion registry: initialized, champion = null (waiting for first full promotion)

---

## 7. Extension Guide (How Another Agent Adds to This System)

### Add a new pipeline stage (Phase 2/3 features)
1. Create `apex_next/lab/<your_module>.py` following the module style: class + docstring + `__main__` self-test.
2. Import and instantiate it in `LabOrchestrator.__init__`.
3. Insert your stage call in `run_experiment_pipeline` at the right point (priority → memory → genealogy → build → gates → registry).
4. If it produces per-experiment data, extend `AuditLedger.append_record` with a keyword arg and pass it from `_log_and_archive`.
5. Update this file (module table + interface spec) and the root README module table.

### Phase 2 backlog (designed, not yet built)
- **Counterfactual Analyzer**: single-decision outcome attribution ("sell 14 units at turn 27 → +12,400 MCV"). Consumes `mcv_replay_dataset.json` rows (has `executed_market_action` + `downstream_wealth_24/120`).
- **Shadow Mode**: candidate mirrors the champion on live telemetry without affecting the match.
- **Research Budget**: e.g. 10 candidate builds / 3 historical suites / 1 blind holdout per day — enforce in orchestrator before Stage 3.
- **Automated experiment recommendation**: feed priority ranking + memory into hypothesis drafting.

### Phase 3 backlog (research frontier)
- Meta-learning across ledger records (which mechanisms survive per archetype).
- Automated failure-archetype discovery (unsupervised clustering of trajectory deltas).
- Opponent strategy clustering (per-opponent behavior models from `opponent_submission_id`).
- Causal decision→outcome analysis.

---

## 8. Real Model Lineage (Context for Anyone Reading This)

| Version | Where | What |
| :--- | :--- | :--- |
| V4.1 | `Ref 55249106` (protected) | Historical champion, 1714.4 live Elo; recovered from `baseline/kaitofukami-v18.py` |
| APEX 3.0 | `Ref 55411304` | State-conditioned MCV; Step 107 synthetic-order bug |
| APEX 3.3 | `Ref 55421857` | Clearance preemption (`step % 24 == 23`); live challenger, ~1105 Elo |
| APEX 3.5 | `generalization_pipeline/submission_candidate_apex35.py` | Dual-Regime Liquidity Priority + Gentle Rebound; 88% WR; vaulted |
| **APEX 3.6** | `submission.py` (PROD) | Seat-conditioned (`step % 24 == 22` for seat 1); 6-gate validated; **currently live and frozen** |

---

## 9. Glossary

- **MCV** — final wealth at match end (the score being maximized)
- **WR** — win rate
- **p05** — 5th percentile of MCV (tail risk)
- **PASS turn** — a turn where the agent took no action (stall signal)
- **Archetype** — a named failure mode (`LIQUIDITY_SHOCK`, …)
- **Challenger** — a candidate that passed all 4 gates
- **Champion** — the current frozen production agent
- **Ledger** — `reports/experiment_ledger.jsonl`, the immutable experiment memory
- **Regime** — a named market state (`SUPPLY_COLLAPSE`, …) from the RegimeDetector

---

## 10. Research Campaign Record — 2026-08-14 (Cycle 1 + OPP-DIFF-1)

**What actually happened (chronological, agent-run, all reproducible).**

### Phase 1 — Fingerprint of the live champion
- Ran `phase1_apex35_fingerprint.py` over the real telemetry dataset (86 trajectories, 43 real
  APEX-lineage matches) → `APEX35_FINGERPRINT.json` + `PHASE1_APEX35_FINGERPRINT_REPORT.md`.
- Findings: mean MCV 68,744 / median 67,188 / p05 25,143; **SUPPLY_COLLAPSE** emerged as the
  priority-3.16 archetype (78/86 trajectories collapse-tagged, 46.2% WR in the tag).
  Provenance note: the dataset is ref **55373438**'s matches, not 55483322.

### Phase 2 — Harness build (the executable gauntlet)
- `apex_next/research/match_runner.py` — paired runner on the real `kaggle_environments`
  kaggriculture env (kaggle-environments 1.32.6, Python 3.13):
  - **Seat-balanced double-run** (2 matches/seed, seats swapped): kaggriculture is
    seat-asymmetric (identical agents differ per seat on some seeds); single-match comparisons
    are confounded — this killed the old single-match protocol.
  - **Determinism verified** byte-identical on reruns (e.g. seed 34083081 → 78,197/65,227 every time).
  - baseline always loaded from `submission.py` (immutable); candidate loaded by explicit path
    (workers re-import modules — never rely on monkey-patching module globals).
- `apex_next/research/gate_runner.py EXP-XXXX <dir>` — Gates 1-4 + statistical judge + ledger +
  registry, resumable via JSON progress files; fail paths write FALSIFIED records to the ledger.
- Legacy `experiments/ablation_*.py` single-match (seed%2) comparisons are **seat-confounded** —
  prior WR claims built on them are unreliable.

### Phase 3 — The falsification stack (ledger: `reports/experiment_ledger.jsonl`)

| EXP | Family | Mechanism | Gate 1 (46 real loss seeds × 2 seats) | Behavior |
| :-- | :-- | :-- | :-- | :-- |
| EXP-0113 | Pricing | sell-gate during collapse (drift≤−30% ∧ below-MA24) | 52.2% WR, +4 MCV | inert (5/46 seeds) |
| EXP-0114 | Pricing | sell-gate below MA24 (broad) | 6.5% WR, −8,126 MCV | harmful (45/46 seeds, cash starvation) |
| EXP-0115 | Capital_Deployment | defer BUY_SEED of collapsing crop | 52.2% WR, +167 MCV | inert (2/46 seeds) |
| EXP-0116 | Pricing | hold MILK/WOOL sells during collapse | 45.7% WR, +784 MCV | fires everywhere (46/46), loses marginal games |
| EXP-0115-CORRECTION | — | VOID (harness bug: candidate_path not passed) | — | corrected, appended |

- Diagnostics that motivated the cycle: sell-path — champion liquidates its cash engine into
  collapse windows (MILK 66, WOOL 44 sells of ~122 collapse steps); buy-path — re-entry buys of
  the collapsing crop (STRAWBERRY 26/123, MELON 8/38, COW 34/100, SHEEP 24/68).
- **Cycle verdict**: the order layer is locally optimized for SUPPLY_COLLAPSE; four honest
  falsifications, no promotion. Cards: `EXP-0113…0116_HYPOTHESIS_CARD.md`.

### Phase 4 — OPP-DIFF-1: opponent-differential study (ledger: `OPP-DIFF-1 → STUDY_COMPLETE`)
Full write-up: `apex_next/research/OPPONENT_DIFFERENTIAL_STUDY.md`. Decision rule pre-registered:
regime is APEX-specific only if collapse WR ≪ elite reference ≥ 10pp.
- **Leg A (real telemetry, 42 matches + 311-match control)**: collapse WR vs elite opponents
  (25.0%) is statistically indistinguishable from APEX's overall WR vs elite (34.2%, Fisher p≈0.52);
  vs tier-2 APEX is BETTER during collapse (+25pp). Collapse duration identical across tiers.
  **The headline 46% was opponent-mix.**
- **Leg B (controlled local round-robin, 360 seat-balanced matches, 30 fresh seeds)**:
  APEX is 3rd of 4 locally — 31.1% WR vs v18 73.3% / apex35 93.3% / v83 2.2%; self-play MCVs
  PROD 57k/85k vs v18 69k/125k and apex35 68k/124k on identical seeds. Gap is GLOBAL strength.
- **Critical sub-finding**: the vaulted apex35 (APEX 3.5) sweeps PROD `submission.py` (3.6)
  **30/30** — the 3.5→3.6 transition looks like a REGRESSION, consistent with the live ladder
  (latest ref 55483322 46.4% vs older ref 55373438 55.6%). Prior 79.2–88% WR claims were
  seat-confounded artifacts.
- **Conclusion**: SUPPLY_COLLAPSE is NOT an APEX-specific weakness → **EXP-0117 is NOT justified;
  the SUPPLY_COLLAPSE thread is closed.** The real opportunity is global strength:
  re-baseline the champion on the seat-balanced harness and verify the 3.5→3.6 regression
  (deferred, requires user decision). Production untouched.

### Harness fixes made during the campaign (regression guards for the future)
1. `match_runner.run_single_match` no longer hard-requires `_STATE` on the candidate module
   (PROD-as-candidate in the round-robin crashed with `AttributeError` → silent 0.0/0.0 ties).
2. `gate_runner` passes `candidate_path` explicitly at all call sites (EXP-0115 wrong-candidate
   bug, recorded as VOID + corrected).

### Hard-won operational lessons
1. Never compare baseline MCVs across runs with different opponents — paired WR is the valid metric.
2. `kaggle_environments.make()` is deterministic given seed, but per-process RNG/import state is
   not a shared assumption; always double-run both seats and verify determinism on reruns.
3. Write ledger records on the FAIL path too — falsifications must be recorded (memory gate contract).
4. The below-MA trigger is a loaded weapon (fires constantly, starves cash); only the calibrated
   regime drift trigger (≤ −30%) is safe to activate.
5. Full-match regime tags are near-universal (100% of round-robin seeds, 91% of real trajectories) —
   regime ATTRIBUTION needs severity/duration splits, not presence tags.
6. Episode agent list order == player_idx order; the `index` field in episode exports is unreliable.

---

## 11. REG-VERIFY-1 — APEX 3.5 vs APEX 3.6 Regression Verification (2026-08-14)

**Status: REGRESSION CONFIRMED** (ledger `REG-VERIFY-1 → REGRESSION_CONFIRMED`).
Script + raw data: `apex_next/research/regression_verify_35_vs_36.py`,
`regression_verify_35_vs_36_results/`. Full report: `regression_verification_report.json`.

### Protocol (identical to Gate-1 holdout)
- **46 real loss seeds** (apex33 cache) × **2 seats per seed** (seat-balanced double-run)
- **Determinism**: 3-seed rerun byte-identical
- Head-to-head apex35 (candidate) vs PROD36 (baseline), plus 4-agent re-baseline on the same seeds

### Head-to-head result (46 seeds × 2 seats = 92 matches, 0 errors)

| Metric | APEX 3.5 (apex35) | PROD 3.6 (submission.py) |
| :-- | --: | --: |
| Seed wins | **46 / 46** | 0 / 46 |
| Win points | **92 / 92** | 0 / 92 |
| Wins by seat | seat0 46/46, seat1 46/46 | 0 / 46 |
| Mean MCV | **104,616** | 45,337 |
| Median MCV | **104,704** | 46,738 |
| P05 MCV | **54,058** | 12,956 |
| Std MCV | 28,247 | 18,999 |
| Binomial p (46/46) | **p < 0.001** | — |

### Re-baseline (completed pairs, 46 seeds each)

| Pair | 3.5-side WR | 3.6-side WR |
| :-- | --: | --: |
| apex35 vs PROD36 | **100.0%** | 0.0% |
| apex35 vs v18 | **69.6%** | — |
| PROD36 vs v18 | — | **0.0%** |
| PROD36 vs v83 | — | 96.7% |

Not completed (run aborted): apex35-vs-v83 (5/46 partial), v18-vs-v83.

### Conclusion
- The 3.5→3.6 transition is a **confirmed regression** on the full seat-balanced holdout:
  3.5 wins every seed on both seats, at 2.3× mean MCV, with a 4.2× p05 advantage.
- Local strength order (from completed pairs): **apex35 > v18 > PROD36 > v83**.
- **Production status: UNCHANGED.** `submission.py` not modified. Restoring/redesignating
  apex35 as champion requires user approval and the release path (release_manager contract).
- Follow-up (pending user decision): research WHY 3.6 degraded (the seat-conditioned
  `step % 24 == 22` rule and the 3.5→3.6 diff are the prime suspects).
