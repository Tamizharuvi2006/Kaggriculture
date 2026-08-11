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
7. **Empirical Population Truth Over Outlier Anecdotes**:
   - Ultra-early Strawberry activation ($\le 72$ steps) appeared in an outlier replay (`kazusw`), but population-wide analysis across 86 competitive match trajectories revealed that $\le 72$ activation has an 83.3% loss rate (16.7% win rate) and collapses mean wealth ($44.3k vs $74.9k).
   - Conventional Day 4.5 activation (Steps 97–120) is the proven optimal meta standard (69.8% of matches, 58.3% win rate, $74.9k mean wealth).

8. **Inventory-Protected Preemption (Surplus-Only Liquidation)**:
   - Siphoning inventory before clearance (`step % 24 == 23`) must never deplete the shed below upcoming batch requirements. Reserving baseline batch quantities prevents morning budget starvation and preserves peak-price 10-unit sales.

9. **Step 71 Targeted Land #2 Liquidity Rescue**:
   - 89.5% of late-Strawberry activation collapses were caused by having <$1,000 liquid cash at Step 96 (Day 4.0). Liquidating surplus Milk & Fertilizer at Step 71 (Day 3 pre-clearance) guarantees >$1,100 cash at Step 96, unlocking Land #2 on time and recovering 100% of late-failure seeds without hurting holdout win rate.

10. **The 3-Quadrant Capex Ceiling Invariant**:
    - Land #4 ($10,000 Capex, SW Quadrant) requires ~46+ Strawberry units and ~288 steps (12 full days) just to break even. In a 720-step (30-day) game, purchasing Land #4 starves operating liquidity and reduces final wealth by -$3,300 to -$4,100 (win rate drops from 68% to 8–12%). Capping land expansion at 3 quadrants is economically optimal.

11. **Production Invariance & Market Realization Dynamics (Steps 336–480)**:
    - Phase 32 and 33 forensic dissections proved that APEX 3.4 maintains 100% production invariance across all 100 fresh holdout seeds (exactly 616 Strawberry units sold, 65 harvest actions, 27 fertilizer applications, and 333 worker actions).
    - The -$6,803 Strawberry revenue difference between Wins and Losses is governed by seed-level market price realization ($162.57/unit on winning seeds vs $151.52/unit on losing seeds) rather than any pipeline breakdown or worker starvation.

12. **Real Kaggle 3000+ Population Invariants & The Clearance Paradox**:
    - Population analysis across 43 real competition matches (86 trajectories) revealed that 3000+ Winners sell only 13.3 Strawberry units on clearance vs Losers who sell 32.6 units (2.5x more!).
    - Winners preserve large full-price batch sales (8.4 units/batch @ $141.08/unit vs $125.82/unit for losers).
    - Reinvestment in Cow Feed & Land #2/3 keeps early cash low (-$150 to -$240 vs losers), but triggers a massive inflection at Day 15 (Step 360: +$2,684 lead), compounding into a +$24,233 final wealth margin.

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
