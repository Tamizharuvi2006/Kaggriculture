# Market-Regime Causal Audit

**Date:** 2026-08-22  
**Mode:** read-only cached-trace analysis  
**Starting authority:** `KAGGRICULTURE_RESEARCH_INDEX.md`

## Scope Guard

No games were run for this audit. No PPO, checkpoint, frozen single-file submission, v18 engine, reward logic, Land #4 logic, production file, or training artifact was modified. The previously failed open-loop milk counterfactual is not used as causal evidence.

## Cached Evidence And Baseline Check

The analysis used the existing `reports/step5b/market_timing_diagnostic/market_timing_diagnostic.json`, `reports/step5b/late_game_economy_audit/late_game_economy_audit.json`, `reports/step5b/candidate_full_trajectory_divergence_32.json`, `reports/step5b/candidate_packaging_equivalence_32.json`, the frozen-PPO milk counterfactual report, and the historical Phase 79-85 market reports.

Baseline reproducibility is accepted from the cached parity evidence:

| Check | Cached result |
|---|---:|
| Research/package paired traces | 32/32 completed |
| Transitions per pair | 720 calls / 719 transitions |
| First divergence | none |
| Full trajectory divergence count | 0 |
| Candidate packaging equivalence | PASS |
| Current economy audit traces | 32 completed |

This is a report-level verification from cached evidence, not a new replay. It establishes that the market observations being summarized came from an accepted frozen baseline. It does not make the missing order-book fields magically recoverable.

## Cohorts

The current PPO market-timing diagnostic defines low MCV as terminal MCV below 60,000 and high MCV as terminal MCV at least 100,000.

| Cohort | Episodes | Mean terminal MCV | MILK covered value | MILK avg covered price | STRAWBERRY covered value | STRAWBERRY avg covered price |
|---|---:|---:|---:|---:|---:|---:|
| Low | 5 | 54,170.0 | 16,933.8 | 51.0 | 15,936.0 | 68.6 |
| High | 13 | 130,581.5 | 80,103.8 | 174.9 | 66,708.0 | 201.8 |
| High minus low | - | **+76,411.5** | **+63,170.0** | **+123.9** | **+50,772.0** | **+133.1** |

Wool is a small separator by comparison: approximately +3,450.8 covered value high minus low.

## Sell-Event Field Audit

### Fields present and usable

The cached event records provide:

- product, step, day, hour, and observed price;
- attempted quantity;
- inventory before the attempted sell;
- inventory-covered quantity;
- inventory shortfall quantity;
- aggregate covered revenue, attempted notional, sell count, high-price exposure, and terminal inventory.

These support price-realization and inventory-coverage analysis.

### Fields absent or not trustworthy enough for causal claims

The cached market-timing records do **not** provide a per-event authoritative:

- opponent sell quantity or opponent order list;
- queue position in the shared order book;
- accepted versus rejected versus preempted outcome;
- cash before and after each individual sell;
- post-clearance price linked unambiguously to that specific order;
- a state digest before and after each individual order.

Therefore the audit uses `inventory_covered_units` as a coverage proxy only. It does not label an event accepted, rejected, or preempted. Opponent identity/profile is available at the episode level, but per-step opponent market activity is not available in the cached artifact.

## Earliest Observable Separation

The first sell timing itself does not separate the cohorts:

- MILK first sell step is 196 in every low and high row inspected.
- STRAWBERRY first sell step is 270 in every low and high row inspected.
- The first MILK prices overlap: low examples include 154, 187, and 206; high examples include 175, 187, 195, 206, and 216.
- The first STRAWBERRY prices also overlap: low examples include 149, 176, and 193; high examples include 163, 184, 186, 193, 201, and 207.
- The first event has zero inventory coverage in the inspected rows, so the first attempted order is not itself evidence of accepted revenue.

The earliest consistently supported signal is therefore **not a single first-sale threshold or first-sale timestamp**. The strongest available early interaction is:

> opponent regime / shared-market pressure interacting with the subsequent product price path and the policy's repeated sell exposure.

This is a ranked causal hypothesis, not a fully identified causal effect. The current traces can show that realized price paths separate later, but cannot attribute each price change to a specific opponent order or queue outcome.

## MILK Findings

- MILK is the largest measured product-level separator: +63,170 high-minus-low covered sell value.
- High-MCV traces attempt more milk volume on average, but the larger difference is price realization: approximately 174.9 versus 51.0 average covered price.
- Low-MCV traces have about 13 high-price-no-sell steps and no measured p90 no-sell exposure in the aggregate diagnostic; high-MCV traces have much larger high-price exposure, about 192 high-price-no-sell steps and substantial p90 exposure. This metric is exposure to high prices while not selling, not proof that waiting would have been beneficial.
- Terminal inventory is zero for both cohorts. The gap is therefore not explained by simply carrying milk to the terminal.
- The paired runtime milk-delay counterfactual reduced MCV in all five low-MCV traces: mean delta -17,275.0. It released only part of removed milk and reduced milk value. This rejects a blanket “hold milk until >=175” explanation.

The best current MILK interpretation is that low-MCV games enter a poor realized-price regime, and a naive delay rule worsens liquidity and downstream production/sales. The causal opportunity, if one exists, is likely state-conditional order placement or queue interaction, not a fixed price hold.

## STRAWBERRY Findings

- STRAWBERRY is the second-largest separator: +50,772 high-minus-low covered sell value.
- Average covered price is approximately 68.6 in low-MCV versus 201.8 in high-MCV traces.
- High-MCV traces also attempt more units, but the price difference is large enough that volume alone cannot explain the gap.
- First sell step and first price overlap across cohorts, so the difference emerges through later price-path realization and repeated clearance behavior.
- As with milk, the cached artifact does not identify whether a specific poor sale was accepted, rejected, or preempted.

## Opponent And Regime Evidence

The economy audit provides a coarse but useful episode-level regime signal:

- `pass_only` opponent cases averaged about 140,239 MCV.
- `v18_baseline` cases averaged about 79,524 MCV and included the 43,502 minimum.
- `apex4_self_play` cases averaged about 79,995 MCV.

This supports opponent participation as a regime correlate. It does not prove that the opponent's sell order caused a particular low-price event, because the cached event records lack opponent action traces aligned to the same market clearing step.

Earlier Phase 79-85 reports provide supporting context: shared-market sells can cause short-term price pressure; elite and normal runs have similar physical production but different market capacity/realization; unilateral withholding and generic batch caps failed or were exploitable. Those results argue against a universal threshold and in favor of a state-and-opponent interaction, while also showing that market-preservation policies can lose through delayed cash realization.

## Alternatives Tested Against The Cached Evidence

| Alternative explanation | Evidence | Assessment |
|---|---|---|
| Land #4 ceiling | Low and high traces both stop at 3 lands; prior Land #4 studies are negative | Not the primary cause |
| Worker/plant/pasture capacity | Low and high structural counts are nearly identical | Not sufficient to explain gap |
| Terminal unsold inventory | Terminal product inventory is zero | Not the main terminal cause |
| First sell timing | Milk step 196 and strawberry step 270 in both cohorts | Rejected as a simple timing-onset explanation |
| Fixed high-price milk threshold | Paired wrapper delta is negative in all low traces | Rejected as a safe causal fix |
| Product quantity alone | Price gaps are much larger than the physical-asset differences | Insufficient |
| Opponent/market regime | Strong episode-level association and prior shared-market studies | Best-supported hypothesis, not fully identified |
| Queue rejection/preemption | Historical reports support it, but current event cache lacks per-event labels | Plausible, currently unverified |

## Final Answers

### 1. Strongest causal hypothesis

The strongest hypothesis is **opponent-conditioned shared-market price realization**: low-MCV games encounter a market/order-flow regime in which repeated milk and strawberry liquidation realizes low prices, while high-MCV games encounter a favorable price path and/or less damaging opponent interaction. The earliest reliable observable is the evolving price/market regime across repeated sells, not the first sell timestamp or a fixed milk threshold.

### 2. Evidence supporting it

- Milk and strawberry explain approximately 113,942 of the measured high-minus-low covered sell-value difference.
- First sell times are identical, while later realized prices diverge sharply.
- Similar farm structures produce 54k versus 130.6k mean MCV.
- Opponent-profile cohorts show large MCV differences, with pass-only much higher than v18/self-play.
- Prior shared-market research independently reports endogenous price pressure and clearance/order interaction.

### 3. Evidence against alternatives

- Land count, workers, plants, and pastures do not separate the cohorts.
- Terminal inventory is zero, so the gap is not simply unsold product at the end.
- First sale timing and first sale price overlap.
- The milk-delay counterfactual is negative, so “wait for 175” is not the cause or a safe fix.
- Direct queue/preemption claims cannot be confirmed from the current cache because the required fields are absent.

### 4. Is a safe counterfactual justified?

**No, not from the current cached data.** A safe counterfactual would first need a baseline-reproducing, state-preserving trace with exact accepted/rejected/preempted order outcomes, cash and inventory deltas, opponent market actions, and downstream prices. The failed open-loop counterfactual must remain excluded.

### 5. Is any new game run worth spending time on?

**No, not yet.** The current blocker is missing causal observability, not insufficient game count. A new run would be worth considering only after a read-only artifact audit confirms that the run can capture the missing per-step fields and reproduce the frozen baseline. Until then, do not spend the requested 7 minutes on another experiment.

