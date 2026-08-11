# 🏗️ APEX System Architecture & Technical Specification

> **Technical Blueprint**: Modular decoupling of Farm Production Foundation (V4.1 Teacher) and Market Execution Optimization (APEX 3.3 Clearance Preemption Engine).

---

## 1. System Design Principles & Decoupling

The APEX architecture operates as a **two-layer decision system**:

```
                       +-----------------------------------+
                       |    WORLD OBSERVATION STATE (obs)  |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       |  RECOVERED V4.1 BASELINE TEACHER  |
                       |  - Closed-Loop Board Expert Route |
                       |  - Daily Worker Task Assignment   |
                       |  - Planned Market Orders List     |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | APEX 3.3 PREEMPTION TIMING ENGINE |
                       |  - Is step % 24 == 23?            |
                       |  - Valid planned sale available?  |
                       |  - Shed Milk >= 2 / Straw >= 4?   |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       |   ACTION EXECUTOR & SAFETY GATE   |
                       |   - Rejects Capital Exploration   |
                       |   - Emits Final Action Schema     |
                       +-----------------------------------+
```

---

## 2. Core Components & Invariants

### 2.1 Recovered V4.1 Foundation (Production Skeleton)
- **Livestock Strategy**: Turn 0 Cow #1 ($400) + Turn 1 Cow #2 ($400). Dual-cow milk production starting Day 2 generates liquid daily cash flow ($\approx \$400-\$600$/day) funding early workforce expansion.
- **Crop Pipeline**: Wheat/Melon opening transitioning on Day 4.4 to Strawberry cultivation (34 strawberry plot target, 31.7% fertilization rate).
- **Worker Allocation**: Closed-loop task paths maintaining 33.1% productive action ratio and only 3.9% idle turns.
- **Land Expansion**: 3-quadrant structure (NW starting, NE at Step 180 / Day 7.5, SW at Step 265 / Day 11).

### 2.2 APEX 3.3 Clearance Preemption Overlay
- **Clearance Boundary Sensing**: Monitors `step % 24 == 23` (1 step prior to Kaggle's daily Town Center clearance boundary).
- **Preemption Criteria**:
  - `MILK`: If `shed["MILK"] >= 2` and no baseline milk sale is queued for turn 23, inject `["SELL", "MILK", milk_qty]`.
  - `STRAWBERRY`: If `shed["STRAWBERRY"] >= 4` and no baseline strawberry sale is queued for turn 23, inject `["SELL", "STRAWBERRY", straw_qty]`.
- **Zero Synthetic Orders Guarantee**:
  - APEX 3.3 NEVER creates artificial sales when inventory is zero.
  - APEX 3.3 NEVER generates capital-consuming actions (`BUY_SEED`, `BUY_LAND`, `HIRE`, `BUY_ANIMAL`).

---

## 3. Monolithic Standalone Build Architecture

Kaggle requires submissions to be single-file Python scripts with zero external dependencies. The monolithic builder script (`experiments/build_standalone_candidate_apex33.py`) constructs `submission_candidate_apex33.py` via structural concatenation:

1. **Base Runtime Constants & Data Tables**: Decompressed b85 runtime matrices for V4.1 expert paths.
2. **Base Agent Subroutine (`_base_agent`)**: Preserves intact V4.1 master baseline logic.
3. **APEX 3.3 Entry Point (`agent(obs, configuration=None)`)**: Wraps `_base_agent` with preemption timing logic and exception fallback handlers.

---

## 4. Verification & Pre-Submission Audit Protocol

Before any build is authorized for upload, it must pass three automated verification gates:
1. **Holdout Tournament Gate**: 50+ unseen seeds evaluated under `townCenterSellInterval = 24`.
2. **Replay Champion Gate**: Evaluated against recorded action schedules of 3200+ rated replay winners.
3. **Schema & Monolithic Audit**: 720-step dry-run simulation verifying non-null action dict schema (`farmer`, `hands`, `market`) and standalone execution with zero errors.
