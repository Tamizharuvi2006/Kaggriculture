# 💡 Key Empirical Research Lessons & Core Invariants

> **Project Wisdom**: Critical takeaways, empirical pitfalls, environment parity discoveries, and non-negotiable safety rules learned during Kaggriculture APEX engineering.

---

## 1. Top Empirical Lessons Learned

1. **Offline Benchmark Superiority Does Not Guarantee Live Kaggle Performance**:
   - APEX 3.0 showed strong offline disagreement metrics against historical replays, but dropped on the Kaggle live ladder from a peak of ~1291 down to 1183.4.
   - **Lesson**: Live human and top-tier opponents react dynamically. Testing against a static recorded action schedule is a pre-submission gate, not a guaranteed live rating result.

2. **Environment Parity Is Non-Negotiable (`townCenterSellInterval = 24`)**:
   - Running local simulations with `townCenterSellInterval = 12` while Kaggle runs at `= 24` created a fundamental mismatch. In a 24-step market, Town Center clears once per day, making clearance-boundary timing (`step % 24 == 23`) critical.
   - **Lesson**: Always verify and enforce exact environment configuration parameters before interpreting simulation results.

3. **Synthetic Orders & Artificial Fallbacks Are Dangerous**:
   - APEX 3.0's Step 107 bug was caused by a fallback rule (`if not candidates: append(["SELL", "WHEAT", 1])`) that injected artificial sales. In a 24-step market, this tiny order clogged market capacity and delayed higher-value sales.
   - **Lesson**: NEVER invent synthetic sales. APEX must only alter the execution timing of legitimate, pre-existing planned sales.

4. **Do Not Fight Game Liquidity with Rigid Batching**:
   - Phase 14 proved that forcing inventory to wait for artificial batch sizes (e.g. Milk $\ge 4$, Strawberry $\ge 6$) caused 17.1 steps of cash starvation, cutting Milk revenue by -55.4% and collapsing win rate to 6.0%.
   - **Lesson**: Immediate liquidity keeps working capital moving. Never hold inventory artificially.

5. **Component Decomposition over Strategy Rewrites**:
   - V4.1 is a recovered 2600+ external baseline. Phases 15–17 proved that V4.1's dual-cow Turn 0/1 opening, Strawberry activation timing (Day 4.4), and worker paths (3.9% idle) are already at 3000+ parity.
   - **Lesson**: Isolate strategy components into modular counterfactuals. Keep proven elite components untouched, and use APEX to optimize only weak components (such as market preemption timing).

6. **Fresh Live Replay Intelligence Over Historical Datasets**:
   - Historical replays from early competition phases lack current top-tier dynamics. Querying recent daily datasets (`manifest.csv`) for 2600–3200+ episode files revealed the exact clearance boundary preemption mechanism.
   - **Lesson**: Use fresh competitive intelligence from recent daily index datasets to guide targeted feature engineering.

---

## 2. Non-Negotiable Safety & Governance Invariants

1. **RULE ZERO**: APEX must NEVER generate capital-consuming exploration actions (`BUY_SEED`, `BUY_LAND`, `HIRE`, `BUY_ANIMAL`).
2. **ZERO SYNTHETIC ORDERS**: APEX must NEVER inject artificial fallback sales or invent market orders.
3. **TIMING OVERLAY ONLY**: APEX 3.3 acts purely as an execution timing overlay on legitimate V4.1 planned sales.
4. **TEACHER FALLBACK**: V4.1 Master Baseline (`Ref 55249106`) is always preserved as the underlying fallback.
5. **ENVIRONMENT PARITY**: All local simulations must run under Kaggle's live parameters (`townCenterSellInterval = 24`).
6. **PROVEN COMPONENT INTEGRITY**: Dual-cow opening (Turn 0/1), Strawberry pipeline, and worker paths remain strictly protected.
7. **MONOLITHIC SUBMISSIONS**: All Kaggle submission artifacts must be 100% self-contained single-file Python builds with no external disk dependencies.
8. **UNSEEN HOLDOUT GATING**: No strategy candidate may be submitted to Kaggle without passing a 50+ seed unseen holdout gauntlet.
9. **BASELINE PROTECTION**: Ref `55249106` (V4.1 Master Champion) is 100% immutable and must NEVER be overwritten or replaced.
10. **SCIENTIFIC CLAIM RIGOR**: Holdout replay-schedule validation must never be claimed as a guaranteed live Kaggle leaderboard score.
