# 📜 APEX Complete Experiment & Phase History

> **Chronological Record of APEX R&D**: From early heuristic modifications to live competitive intelligence and the APEX 3.3 Clearance Preemption Engine.

---

## 1. APEX 2.x Foundations (Phases 1–7)

### Phase 1 — End-Game Liquidation Guard
- **Hypothesis**: Forcing market liquidations in the final 48 steps of an episode would maximize final cash.
- **Empirical Result**: Caused -$5.1k degradation in final wealth and a 0/4 win rate in local testing.
- **Decision**: Permanently killed and discarded.

### Phase 2 — APEX 2.0/2.1 Imitation Engine
- **Hypothesis**: Training a multi-layer neural/heuristic world model to imitate top-tier teacher trajectories would produce autonomous high-level play.
- **Empirical Result**: Achieved high action imitation accuracy, but produced near-0% strategic discovery and suffered extreme teacher dependency.
- **Decision**: Frozen as historical research.

### Phase 3 — APEX 2.2/2.3 Capital Exploration Catastrophe
- **Hypothesis**: Allowing the APEX planner to explore capital-consuming actions (`BUY_SEED`, `BUY_LAND`, `HIRE`, `BUY_ANIMAL`) would discover optimal expansion timing.
- **Empirical Result**: Catastrophic capital collapse. Mean ending cash dropped from $128k to $4.7k due to premature land purchases and worker over-hiring that starved crop seed capital.
- **Decision**: Established **RULE ZERO** (*APEX must never explore capital-consuming actions*).

### Phase 4 — Invariant Hardening & Safety Filtering
- **Implementation**: Evaluated 13,720 candidate actions across 8,628 simulation steps. Approximately 960 passed strict safety checks.
- **Decision**: Established deterministic safety filtering for all downstream APEX candidates.

### Phase 5 — APEX 2.5-C First Live Divergence
- **Achievement**: First successful live inventory divergence on Seed 590244349 at Step 100.
- **Result**: `SELL_WHEAT_1` produced a +$4 wealth gain over baseline.

### Phase 6 — APEX 2.5-F Marginal Counterfactual Value (MCV)
- **Breakthrough**: Replaced naive spot-cash evaluation with Marginal Counterfactual Value (MCV), evaluating downstream wealth impact rather than immediate money.
- **Result**: Reduced valuation Mean Absolute Error (MAE) from $267.41 to $1.77.

### Phase 7 — APEX 2.5-G Control Baseline
- **Validation**: 12-match sweep produced 12/12 wins and a +$16 net wealth delta against earlier baselines.
- **Decision**: Frozen as the local control baseline.

---

## 2. APEX 3.0 Offline R&D (Phases 8–13)

### Replay Data Extraction & Schema
- Extracted 5,160 state-action-outcome tuples from 43 top-tier replay files (`kaggriculture-episodes-index` and `l+reviews/`).
- **Tuple Schema**: `(episode_id, step, cash, inventory, unlocked_land, workers, market_prices, storage_congestion, expert_action, actual_action, downstream_wealth_deltas, final_wealth, win_loss)`.

### Key Empirical Findings
1. **Wheat Liquidation State Dependence**: Selling wheat when cash $< \$300$ strongly correlated with lower win rates due to loss of seed buffer.
2. **Fertilizer Phase Dependence**: Early fertilizer sales severely degraded crop yield, whereas late-game fertilizer sales generated clean liquidation value.
3. **Storage Congestion**: Dynamic storage congestion relief provided measurable marginal value when inventory exceeded 45% of plot capacity.

### APEX 3.0 Model Architecture
- Integrated `EmpiricalMarginalEvaluator`, liquidity-aware multipliers, early fertilizer suppression, and dynamic congestion relief.
- Passed 12-seed comparisons, 132-state disagreement analysis, 16-seed blind holdouts, and 50-seed integrated gauntlets.

### Kaggle Submission & Live Failure Analysis
- **Submission**: Ref `55411304` (`submission_candidate_apex30.py`).
- **Observed Public Score**: Peaked at ~1291 before declining to **1183.4** (with repeated losses around the 1200+ rating band).
- **Core Lesson**: Offline benchmark superiority against historical replays did NOT guarantee live Kaggle leaderboard performance due to environment mismatch and synthetic order interference.

---

## 3. Environment Parity & Bug Forensics (Phases 14–15)

### Phase 14 — Town Center Clearance Parity Discovery
- **Discovery**: Local simulation default was `townCenterSellInterval = 12`, while live Kaggle environment runs at `townCenterSellInterval = 24`.
- **Impact**: In a 24-step market, Town Center clears once per day. Orders remain in the market twice as long, making market preemption and slot capacity critical.
- **Inventory Batching Test**: Proved that holding Milk/Strawberry for artificial batch sizes caused 17.1 steps of cash starvation, cutting Milk revenue by -55.4% and collapsing win rate to 6.0%.

### Phase 15 — Step 107 Bug Isolation & APEX 3.2
- **Forensics**: Traced APEX 3.0's live failure to **Step 107** (Day 4 / Hour 11).
- **Root Cause**: `ActionPlanner` contained an artificial fallback (`if not candidates: append(["SELL", "WHEAT", 1])`) that injected synthetic market orders. Under 24-step clearance, this tiny order clogged market capacity and delayed higher-value sales.
- **Fix (APEX 3.2)**: Completely removed the artificial fallback. Produced exact trajectory equality with control on 50-seed parity tests. APEX 3.2 was frozen locally without upload.

---

## 4. Component Deconstruction & Forensics (Phases 16–18)

### Phase 16 — Animal Staging Counterfactual Lab
- **Hypothesis**: Delaying Cow #2 to Day 2 (Step 24) to scale workers first.
- **Tournament Result (50 unseen seeds vs V4.1 Master)**:
  - Arm A (Fixed Staging): **0.0% Win Rate (0W-50L)**
  - Arm B (Labor Gated): **0.0% Win Rate (0W-50L)**
  - Arm C (Dynamic Runway): **0.0% Win Rate (0W-50L)**
- **Causal Finding**: Dual-cow opening on Turn 0 & Turn 1 generates $\approx \$400-\$600$ daily milk revenue starting Day 2, funding workers and strawberry seeds. Delaying Cow #2 destroys compounding growth.
- **Decision**: Dual-cow opening is **PROVEN ELITE & KEEP**.

### Phase 17 — Strawberry Production & Worker Allocation Forensics
- **Analysis**: Compared 71 Top-Tier Replays vs 30 V4.1 simulation trajectories under 24-step parity.
- **Findings**:
  - Strawberry Activation: Top-Tier Day 4.8 (Step 115) vs V4.1 Day 4.4 (Step 106).
  - Seeds Bought: Top-Tier 42.6 vs V4.1 44.0.
  - Fertilizer Rate: Top-Tier **31.8%** vs V4.1 **31.7%**.
  - Worker Idling: Top-Tier **6.7%** vs V4.1 **3.9%**.
- **Decision**: V4.1's Strawberry cultivation engine and worker paths are **PROVEN ELITE & KEEP**.

### Phase 18 — Live Competitive Intelligence & Clearance Preemption
- **Dataset**: Selectively fetched 15 recent 2600–3200+ replay files from daily Kaggle index (`manifest.csv`, dates 2026-08-07 to 2026-08-09).
- **Major Finding**: **100% of divergence events in 3000+ matches occur at 24-step clearance boundaries (`step % 24 == 23`)**.
- **Clustering**: 73.3% Milk Preemption, 26.7% Strawberry Preemption. Major divergence clusters at Step 360 (Day 15 clearance) and Step 450 (Day 18 clearance).

---

## 5. APEX 3.3 Clearance Preemption & Validation (Phases 19–20)

### Phase 19 — Clearance Preemption Counterfactual Lab
- **Architecture**: APEX 3.3 operates purely as a **timing overlay** on legitimate V4.1 planned sales, advancing execution timing to `step % 24 == 23` if Milk $\ge 2$ or Strawberry $\ge 4$.
- **Tournament Result (50 unseen seeds vs V4.1 Master)**:
  - Control (V4.1 Master): **62.0% Win Rate** ($94.5k wealth)
  - Arm A (Milk Preemption): **72.0% Win Rate** ($79.1k milk rev)
  - Arm B (Straw Preemption): **70.0% Win Rate** ($92.4k straw rev)
  - **Arm C (Combined APEX 3.3)**: 🔥 **74.0% Win Rate** (+12.0% win rate jump, +$6,564.88 gross revenue delta, 0 synthetic orders, 0 cash starvation penalty).

### Phase 20 — Multi-Opponent Validation Gate & Submission
- **Holdout Test (50 unseen seeds `80000+`)**:
  - Vs V4.1 Master Baseline: 🔥 **84.0% Win Rate (42W-8L)** ($95,392 vs $94,614 mean wealth).
  - Vs Historical APEX 3.0: 🔥 **84.0% Win Rate (42W-8L)**.
- **Strong Replay Opponent Test (50 unseen seeds `90000+`)**:
  - Vs 3200+ Live Replay Champion Expert (`91153990.json`): 🔥 **100.0% Win Rate (50W-0L)** ($125,803 vs $85,007 mean wealth).
- **Standalone Audit**: Monolithic build [`generalization_pipeline/submission_candidate_apex33.py`](file:///D:/kaggriculture/generalization_pipeline/submission_candidate_apex33.py) passed 100% schema, syntax, and standalone execution checks.
- **Kaggle Submission**: Uploaded as **Ref `55421857`** on 2026-08-11.
