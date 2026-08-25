# 📂 Kaggriculture Project — Data & File Index

> **Purpose**: Quick reference for any agent to find exactly what data exists and where.
> **Updated**: August 17, 2026

---

## 🟢 PRODUCTION AGENTS (The Only Working Code)

| File | Lines | Size | What It Is |
|:---|:---|:---|:---|
| `submission.py` | 4,572 | 316 KB | **LIVE on Kaggle** — APEX 3.5 full tournament agent |
| `APEX4_SUBMISSION_FINAL.py` | 4,635 | 319 KB | **SEALED** — APEX 4.0 with 4 adaptive rules, ready to deploy |
| `APEX35_ROLLBACK_ARCHIVE/submission_apex35_prod_backup.py` | 4,572 | 316 KB | Byte-identical backup of APEX 3.5 for rollback |

---

## 📜 GOVERNANCE & RELEASE DOCS

| File | What It Contains |
|:---|:---|
| `README.md` | Master project documentation (15 sections, game format, architecture, history) |
| `BASELINE_CONTRACT.md` | Release governance rules — 4-gate system, statistical thresholds, audit schema |
| `RELEASE_CHECKLIST.md` | Pre-launch verification matrix (all items verified for APEX 4.0) |
| `KAGGRICULTURE_CURRENT_STATE.md` | Operational status summary |
| `TODO.md` | Roadmap, next steps, ML requirements |
| `APEX4_PROVENANCE.json` | How APEX 4.0 was built — research phases, rule definitions, invariants |
| `APEX4_RELEASE_MANIFEST.json` | All 4 gate results with exact metrics |
| `APEX4_SHA256.txt` | Certified checksums for candidate + backup |
| `KAGGLE_RATING_TIMELINE_RECONSTRUCTION.md` | Full rating history across all submissions |

---

## 📊 REPORTS (347 files in `reports/`)

### APEX 4.0 Validation Reports
| File | What It Contains |
|:---|:---|
| `APEX4_GATE_REPORT.json` | Gate 1 results (67.4% WR on 46 loss seeds) |
| `APEX4_HOLDOUT_REPORT.json` | Gate 3 results (71.0% WR on 100 unseen matches) |
| `APEX4_EXTREME_STRESS_REPORT.json` | Extreme asymmetry stress test (12/12 improved) |
| `APEX4_LIVE_LOSS_REGRESSION.json/.md` | 30 real Kaggle loss replay (18/30 recovered) |
| `APEX4_SHADOW_REPORT.json` | Shadow match comparison |
| `APEX4_POLICY_RULES.json` | All 10 validated policy rules with triggers and payoffs |
| `APEX4_ARCHITECTURE.md` | Decision flow architecture |
| `APEX4_RELEASE_DECISION.md` | Formal release decision document |
| `APEX4_TASK_GRAPH.json` | Task graph structure |
| `APEX4_WORLD_MODEL.md` | World model specification |
| `APEX4_MACRO_ECONOMIC_REPORT.md` | Macro economic analysis |

### Phase Research Reports (Phase 66–107)
| Pattern | Count | What They Cover |
|:---|:---|:---|
| `PHASE66_*` through `PHASE107_*` | 42 files | Mid-tier failure decomposition, opponent clustering, elite tier decomposition, market causality, seat asymmetry, engine validation |

### Experiment Screening Reports (EXP-0118 through EXP-0155)
| Pattern | Count | What They Cover |
|:---|:---|:---|
| `EXP0118_*` through `EXP0155_*` | 72 files | GPU screening, guardrail audits, forensic validations, paired simulations, solvency audits, worker eligibility, seed lifecycle |

### GPU Engine Reports
| Pattern | What They Cover |
|:---|:---|
| `PAIRED_GPU_V2_*` | V2 engine design, benchmark, parity testing |
| `PAIRED_GPU_V25_*` | V2.5 engine benchmark, parity, profiling, animal lifecycle |

### Research Cycle Meta-Audits
| Pattern | Count | What They Cover |
|:---|:---|:---|
| `RESEARCH_CYCLE_*` | 20 files | Cycles 2–11 meta-audits and top-5 hypothesis queues |

### Strategy Variant Reports
| Pattern | What They Cover |
|:---|:---|
| `V4_*` through `V13_*` | Head-to-head audits, MPC controllers, deployment rehearsals |
| `COMPETITIVE_HYBRID_*` | Hybrid V2–V5 verification, wealth analysis, ceiling analysis |
| `CANDIDATE_LPLUS_*` | L+ / L++ / L+++ stress tests and verification |
| `SPATIAL_POLICY_*` | Spatial policy forensics, world models, architecture |

### Live Match Telemetry
| File | What It Contains |
|:---|:---|
| `LIVE_APEX35_MATCH_TRACKER.md` | Full APEX 3.5 match tracker |
| `LIVE_KAGGLE_MATCH_FORENSICS_AUDIT.md` | Forensic audit of live matches |
| `LIVE_KAGGLE_MATCH_TELEMETRY.md` | Telemetry summary |
| `APEX35_LIVE_LOSS_REGRESSION.json` | APEX 3.5 recent loss data |
| `reports/live_match_telemetry/` | Raw Kaggle episode JSON exports (807 matches) |

### Core Infrastructure
| File | What It Contains |
|:---|:---|
| `experiment_ledger.jsonl` | **Append-only audit trail** — every experiment ever run |
| `champion_registry.json` | Current champion record |
| `priority_audit_report.json` | Research priority rankings |

---

## 🔬 RESEARCH SCRIPTS (`research/`, 100 files)

### Live Match Analysis
| File | What It Does |
|:---|:---|
| `audit_all_live_submissions.py` | Extracts exact match records from all 10 live submissions |
| `analyze_apex35_live_matches.py` | Analyzes APEX 3.5 live performance |
| `analyze_recent_apex35_losses.py` | Deep analysis of recent losses |
| `fetch_our_kaggle_matches.py` | Fetches match data from Kaggle API |
| `inspect_35_losses.py` | Inspects specific loss matches |

### Forensic Analysis (Phase Scripts)
| Pattern | Count | What They Cover |
|:---|:---|:---|
| `phase15_*` through `phase107_*` | 55 files | Production capacity, strawberry workers, market preemption, loss dissection, opponent divergence, real population study, elite strategy reconstruction, tile lifecycle, crop cycles, worker allocation, sale decisions, market velocity, engine benchmarks |

### Replay & Data Processing
| File | What It Does |
|:---|:---|
| `replay_parser.py` | Parses Kaggle replay format |
| `behavior_extractor.py` | Extracts behavioral features from replays |
| `build_mcv_replay_dataset.py` | Builds the MCV replay dataset |
| `strategy_discovery.py` | Strategy discovery pipeline |

---

## 🏗️ RESEARCH INFRASTRUCTURE (`apex_next/`)

### `apex_next/lab/` — 17-Module Autonomous Research Lab
| Module | What It Does |
|:---|:---|
| `orchestrator.py` | Wires all 16 stages end-to-end |
| `telemetry_ingestor.py` | Parses real Kaggle episode exports |
| `diagnostics_analyzer.py` | Classifies losses into failure archetypes |
| `hypothesis_generator.py` | Generates single-variable hypotheses |
| `candidate_builder.py` | Creates isolated experiment branches |
| `exact_replay_engine.py` | **Gate 1** — exact loss seed replay |
| `historical_suite_engine.py` | **Gate 2** — 50-seed historical regression |
| `frozen_holdout_engine.py` | **Gate 3** — 100-seed frozen holdout |
| `statistical_judge.py` | **Gate 4** — 6-dimension statistical certification |
| `release_manager.py` | Sole write authority for submission.py |
| `experiment_memory.py` | Hypothesis memory + genealogy tracking |
| `priority_engine.py` | Impact × Frequency × Confidence × Fixability ranking |
| `regime_detector.py` | Market regime classification |
| `artifact_hasher.py` | SHA-256 provenance bundling |
| `regression_sentinel.py` | Live match regression monitoring |
| `champion_registry.py` | Promotion/demotion bookkeeping |

### `apex_next/apex4/` — APEX 4.0 Architecture
| File | What It Contains |
|:---|:---|
| `controller/apex4_controller.py` | Main APEX 4.0 controller |
| `controller/apex4_regional_controller.py` | Regional controller variant |
| `controller/apex4_state_driven_controller.py` | State-driven variant |
| `task_graph/task_graph.py` | Task dependency graph |
| `world_model/world_model.py` | Game world model |
| `opponent_model/opponent_tracker.py` | Opponent behavior tracker |
| `counterfactual/counterfactual_engine.py` | Counterfactual analysis engine |

### `apex_next/gpu_engine/` — ⚠️ Needs Rebuild
| File | Status | What It Does |
|:---|:---|:---|
| `cuda_batch_engine.py` | ❌ TOY | NumPy milk-only simulator (not CUDA) |
| `paired_sim_v2.py` | ❌ TOY | Milk+wool only, no crops/workers |
| `python_ref_engine.py` | ⚠️ PARTIAL | Python reference simulator |
| `differential_tester.py` | ❌ MOCK | Claims parity but never calls kaggle_environments |
| `paired_gpu_v25/` | ❌ MOCK | Extended toy simulator with mock validators |

### `apex_next/ml_engine/INVALIDATED/` — ❌ Dead ML Branch
See [`INVALIDATED/README_INVALIDATED.md`](file:///D:/Kaggriculture/apex_next/ml_engine/INVALIDATED/README_INVALIDATED.md)

### `apex_next/ml_engine/README_ML_PLAN.md` — 🧠 Hybrid ML Upgrade Plan
Complete implementation specification for the 3-layer hybrid ML architecture. Contains:
- Exact PyTorch model definitions with code
- 128-dim feature extractor with all field mappings
- PPO training pipeline (9 steps)
- Integration points into submission.py (exact line numbers)
- Packaging instructions for Kaggle
- Anti-patterns to avoid (lessons from the failed pipeline)

See [`README_ML_PLAN.md`](file:///D:/Kaggriculture/apex_next/ml_engine/README_ML_PLAN.md)

---

## 📦 ROOT-LEVEL DATA FILES

### Research Results (moved to `research_results/`)
| Pattern | Count | What They Contain |
|:---|:---|:---|
| `research*_results.json` | 22 files | Scheduler audit, seed oracle, ROI, cow replacement, liquidity shock, counterfactual, robustness, feed insurance, market order, herd frontier, etc. |
| `*_checkpoint.json` | 5 files | Experiment checkpoints (melon curve, baseline, feed, reserve floor, research32) |
| `phase_*_results.json` | 3 files | Post-day-15 divergence, market truncation, worker action results |
| `v4*_results.json` | 6 files | Strategy variant head-to-head results |

### Other Root Files
| File | Size | What It Contains |
|:---|:---|:---|
| `data/replay/mcv_replay_dataset.json` | 3.3 MB | Real per-step replay dataset (5,160 rows / 86 trajectories) |
| `behavioral_divergence_results.json` | 394 KB | Full behavioral divergence analysis |
| `data/replay/manifest.csv` | 1.8 KB | Kaggle episode dataset manifest |
| `requirements.txt` | 59 B | Python dependencies |
| `data/notebooks/what-actually-wins-on-the-kaggriculture-ladder.ipynb` | 978 KB | Kaggle notebook analysis |
| `APEX41_SUBMISSION_FINAL.py` | 291 KB | ❌ BROKEN STUB — do not deploy |

---

## 🗺️ Quick Search Guide

| I need to... | Look in... |
|:---|:---|
| Understand the game format | `README.md` Section 3 |
| See how the agent works | `submission.py` (the actual code) |
| Understand APEX 4.0 rules | `APEX4_PROVENANCE.json` or `README.md` Section 5 |
| Check gate results | `APEX4_RELEASE_MANIFEST.json` |
| See live match history | `reports/LIVE_APEX35_MATCH_TRACKER.md` |
| Find a specific experiment | `reports/experiment_ledger.jsonl` (grep for EXP-XXXX) |
| See what research was done | `reports/RESEARCH_CYCLE_*` or `research/phase*.py` |
| Understand the release process | `BASELINE_CONTRACT.md` |
| See why ML failed | `apex_next/ml_engine/INVALIDATED/README_INVALIDATED.md` |
| Build a new ML agent | `apex_next/ml_engine/README_ML_PLAN.md` (full spec with code) |
| Deploy APEX 4.0 | `README.md` Section 13 |
| Roll back to APEX 3.5 | `README.md` Section 13 |
| Parse real Kaggle replays | `apex_next/lab/telemetry_ingestor.py` |
| Run experiment pipeline | `apex_next/lab/orchestrator.py` |
