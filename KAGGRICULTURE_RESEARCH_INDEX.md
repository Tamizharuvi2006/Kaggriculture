# Kaggriculture Research Index

**Created:** 2026-08-22  
**Purpose:** consolidated map of existing research in `D:\Kaggriculture` before any new diagnosis or model change.  
**Scope:** read-only inventory and synthesis. No games, training, optimization, submissions, checkpoint edits, production edits, or frozen-candidate edits were performed for this index.

## Executive Status

The repository already contains a large multi-generation research record. The strongest current evidence says:

- Physical production and the normal 3-land progression are broadly saturated in strong runs.
- The largest high-vs-low MCV separator is realized market value, especially milk and strawberry price/capture, with wool a smaller contributor.
- Shared-market interaction, order-queue contention, sell timing, and opponent strength have all been studied in multiple generations.
- Generic milk holding and unilateral market-preservation rules were already rejected or neutral in earlier controlled work.
- The newest frozen-PPO diagnostics confirm a milk price/MCV correlation but do **not** support a simple milk-delay rule: the paired runtime counterfactual reduced terminal MCV in every low-MCV trace.
- Land #4 is not a justified next change. It is affordable in the audited PPO traces, but prior controlled land-expansion evidence is negative and both high and low PPO outcomes end at 3 lands.
- The remaining useful gap is a tightly specified causal explanation of why the same frozen policy realizes very different milk/strawberry values under different opponent/market regimes, using existing traces before any implementation.

## Inventory And Method

The current filesystem contains approximately 3,100 research and runtime artifacts, including:

| Extension | Count | Main use |
|---|---:|---|
| `.json` | 1,156 | experiment results, manifests, reports, traces |
| `.py` | 762 | engines, audits, analysis, experiment runners |
| `.md` | 346 | reports, decisions, notes, governance |
| `.npz` | 85 | cached numeric datasets/traces |
| `.pt` | 53 | checkpoints |
| `.pyc` | 199 | generated runtime files |
| `.txt` | 14 | checksums, notes, logs |
| `.log` | 7 | execution logs |
| `.csv` | 2 | tabular replay/experiment indexes |
| `.jsonl` | 2 | experiment and policy ledgers |
| `.ipynb` | 1 | notebook research artifact |
| `.zip` | 3 | release/package archives |

The synthesis used the root and subdirectory inventory, project/current-state maps, research meta-audits, experiment ledger, phase reports, APEX/PPO reports, cached replay manifests, and the latest `reports/step5b` diagnostics. Existing dirty-worktree deletions were preserved; deleted files were not restored or treated as current readable evidence.

## Authoritative Navigation

- Current operational state: `KAGGRICULTURE_CURRENT_STATE.md`
- Project map: `KAGGRICULTURE_PROJECT_MAP.md`
- Data map: `DATA_INDEX.md`
- Governance: `BASELINE_CONTRACT.md`, `RELEASE_CHECKLIST.md`
- Research governance: `reports/RESEARCH_META_AUDIT.md`, `reports/CAUSAL_CONFUNDING_LEDGER.json`, `reports/experiment_ledger.jsonl`
- Historical reconstruction: `reports/RESEARCH_RECONSTRUCTION_AUDIT.md`
- Latest frozen-PPO diagnostics: `reports/step5b/`

## Timeline And Conclusions

### V4.1 / v18 baseline and early APEX history

- `baseline/kaitofukami-v18.py` and related reconstruction reports describe the dynamic closed-loop baseline: early cows, land progression, continuous production, feed protection, and clearance behavior.
- The 15-melon opening was linked to early cash starvation; the 10-melon opening improved liquidity in L+ research.
- Unranked market orders were vulnerable to shared order-queue preemption; milk priority at high prices was identified as a meaningful historical weakness and later tested in L+.
- Static-cap and modular-intent branches performed poorly against dynamic opponents. V5 was permanently rejected after losing all paired matches in its documented run; V8.3 collapsed in live rating and was rolled back.

### L+, L++, hybrid, and APEX ladder research

- Historical L+/L++/hybrid/APEX submissions produced both 1000+ scores and later losses. The recoverable-loss gauntlet contains 15 historical loss traces, each 719 transitions, and the frozen PPO defeated all 15 open-loop historical opponent traces. This is useful replay evidence, not proof against adaptive source agents.
- The strongest recoverable historical opponent traces include L++ around 146,972 MCV, APEX35 around 99,991, APEX30 around 99,012, and several 76k-108k opponents.
- Candidate-vs-four-opponent validation and full trajectory parity reports show the packaged PPO candidate is mechanically valid and equivalent to its research source for the audited seeds.
- Earlier L+ reports claim strong synthetic generalization, but the repository itself distinguishes synthetic/local worlds from live Kaggle matchmaking. Do not use synthetic sweeps as live-rating proof.

### APEX4.1 ML / PPO history

- The original APEX4.1 branch was invalidated for synthetic observations, fabricated metrics, non-parity behavior, hardcoded validators, and invalid action artifacts. Those files remain audit evidence only.
- The rebuilt pipeline has valid intermediate dataset/classifier/PPO mechanics artifacts. The 500-episode learning pilot was operationally healthy but showed no clear learning trend; no checkpoint was promoted and long training was not started.
- Step 5B OPT-6/OPT-7 rollout and parity gates passed. The PPO candidate remains frozen for the current diagnostic line.

### Research cycles EXP-0113 through EXP-0120

The research meta-audit records eight attractive solo-screen results that failed official paired exact replay, generally at 50% or neutral MCV delta:

| Experiment | Tested hypothesis | Existing verdict |
|---|---|---|
| EXP-0113 | collapse exit timing | falsified under paired gate |
| EXP-0114 | moving-average sell suppression | falsified |
| EXP-0115 | seed-buy deferral | falsified |
| EXP-0116 | milk/wool hold | falsified/neutral |
| EXP-0117 | safe cash buffer | falsified |
| EXP-0118 | late milk timing | falsified at official gate; separate audit reports price slippage from delayed liquidation |
| EXP-0119 | plant priority | falsified/neutral |
| EXP-0120 | tri-crop portfolio | falsified/neutral |

The durable lesson is that isolated solo screening is not predictive when both players share the market order book and seat symmetry is enforced.

### Land and capital progression

- EXP-0121 found unconditional early Land 2 expansion harmful: 4.3% win rate and approximately -$4,069 MCV.
- EXP-0124 found solvency-gated expansion approximately neutral rather than a durable competitive edge.
- Existing Land #4 reports are negative: naive and state-aware Land #4 variants underperformed the control; a separate forensic report shows 4-land trajectories below 3-land trajectories on average.
- Latest PPO audit: 32/32 traces stopped at 3 lands; all audited traces were Land #4 cash-affordable while at 3 lands. Low-MCV and high-MCV groups both stopped at 3 lands with nearly identical workers, plants, and pastures. Therefore Land #4 is a secondary capacity question, not the demonstrated cause of the low tail.

### Market and opponent research, Phases 66-107

The phase reports contain repeated, partially overlapping investigations:

- Physical production is near saturation in elite and normal runs; production quantity alone does not explain the large wealth gap.
- Price paths and market capacity explain a large part of elite-vs-normal economic-pie differences. Favorable price regimes can produce 120k-150k outcomes for otherwise similar physical farms.
- Selling volume has endogenous short-term price impact, especially for strawberry and milk. Large batches can compress the next price, but unilateral withholding is exploitable by an opponent and can delay cash realization.
- Opponent-aware market equilibrium, market capture, seat asymmetry, clearance timing, first divergence, and micro-compounding were all studied. Some proposed market-preservation or opponent-responsive policies failed head-to-head gates despite attractive local metrics.
- Elite replay reverse engineering repeatedly identifies early land timing, saturated production, liquidity preservation, and concentrated clearance/preemption windows as common behavior. It does not establish a universal fixed sell threshold.
- EXP-0122 established that opponent private shed inventory is not legally observable; any strategy depending on direct opponent inventory is invalid.
- EXP-0123 established that town wheat inventory is too deep for practical denial; feed-denial via town-pool depletion is invalid.

## Tested And Rejected / Do Not Repeat

The following are explicitly closed, rejected, invalid, or already sufficiently tested for the current question:

- Original APEX4.1 synthetic/classifier branch.
- V5 modular-intent architecture.
- V8.3 static strategy.
- Candidate C conditional Cow 9-10 expansion.
- Generic milk holding / deferred sales as a blanket rule.
- Generic milk/wool hold and late milk timing as a standalone fix.
- Second crop-cycle forcing.
- Unconditional early Land 2 expansion.
- Solvency-gated land expansion as a presumed competitive edge.
- Land #4 implementation as the next fix.
- Unilateral market preservation, broad batch capping, and passive price waiting.
- Solo GPU candidate scores without paired shared-market validation.
- Opponent private-inventory front-running.
- Town-shop wheat denial.
- Retraining or random PPO tuning before causal diagnosis.

## Validated Findings

- Frozen PPO packaging and research-vs-release trajectory parity passed the recorded audits.
- Frozen PPO defeated all 15 recoverable historical loss replay traces in the open-loop gauntlet, with the adaptive-opponent caveat.
- 3-land progression is mechanically consistent in current PPO traces.
- High and low PPO MCV groups have similar physical asset counts; market realization is the larger observed separator.
- Low-vs-high current PPO audit measured approximate covered sell-value gaps of +$63,170 milk, +$50,772 strawberry, and +$3,451 wool in favor of high-MCV traces.
- Current cohort averages measured milk sell price near $51 in low-MCV traces versus about $175 in high-MCV traces; strawberry showed a similarly large separation.
- Prior phase work independently supports shared-market price pressure, favorable market-regime effects, and the importance of clearance timing.

## Current Low-MCV / Market-Regime Question

### Already answered or partially answered

1. The gap is not primarily explained by worker count, pasture count, plant count, or simply stopping at 3 lands.
2. Milk and strawberry realized prices are strongly associated with the gap; wool is smaller.
3. Market prices are affected by both price-regime opportunity and shared-market actions.
4. A naive policy that removes milk sells below a high threshold and waits for the next high window is not causal rescue evidence. In the latest dynamic wrapper, it lowered terminal MCV in all five low-MCV traces, released only part of the removed quantity, and left pending milk; mean MCV delta was negative.

### Not yet answered cleanly

- Which observable market state at the exact sell decision predicts whether milk should be sold now, partially sold, or retained without causing liquidity damage?
- How much of the low-MCV milk gap comes from accepted versus rejected/preempted orders, versus genuinely low market prices, versus inventory/cash timing?
- Whether the relevant regime variable is opponent sell pressure, market-pool inventory, price trend, clearance-step position, action-order position, or an interaction of these.
- Whether a quantity-preserving, cash/reserve-preserving counterfactual can alter only sell order placement while reproducing the same dynamic baseline state. The earlier open-loop replay counterfactual failed baseline reproduction and must not be used as causal evidence.
- Whether milk and strawberry are coupled through shared market pressure in the low-MCV cases, or whether one is an upstream driver and the other a consequence.

## Reusable Cached Evidence

- `data/replay/mcv_replay_dataset.json` and `data/replay/manifest.csv`: replay dataset and manifest.
- `reports/step5b/old_loss_gauntlet/raw_replays/`: recoverable 719-transition historical loss traces.
- `reports/step5b/old_loss_gauntlet/old_loss_gauntlet_report.json`: frozen-PPO historical-loss comparison.
- `reports/step5b/candidate_vs_four_opponents_32.json`: current candidate opponent comparison.
- `reports/step5b/candidate_full_trajectory_divergence_32.json`: packaged/research parity.
- `reports/step5b/late_game_economy_audit/`: 32 PPO trace economy audit.
- `reports/step5b/market_timing_diagnostic/`: current milk/strawberry/wool cohort statistics.
- `reports/step5b/milk_sell_counterfactual/`: dynamic wrapper counterfactual and its negative result.
- `reports/PHASE71_MILK_REVENUE_REPORT.md`, `PHASE79_MARKET_CAUSALITY_REPORT.md`, `PHASE80_SALE_IMPACT_ELASTICITY_REPORT.md`, `PHASE81_OPPONENT_AWARE_EQUILIBRIUM_REPORT.md`, `PHASE82_MARKET_CAPTURE_FORENSICS_REPORT.md`, `PHASE83_CAUSAL_SOURCE_LOCALIZATION_REPORT.md`, `PHASE84_FACTORIAL_DECOMPOSITION_REPORT.md`, `PHASE85_OPPONENT_ADAPTIVE_EXPLOITATION_REPORT.md`.
- `reports/CAUSAL_CONFUNDING_LEDGER.json`, `reports/LOSS2POLICY_DATASET.jsonl`, `reports/experiment_ledger.jsonl`, and the `EXP012x`/`EXP013x`/`EXP014x`/`EXP015x` evidence files.
- `reports/step3h/traces/`, `reports/step3h/parity/`, `reports/step3h/cuda/`: cached engine parity traces and performance evidence; do not rerun unless a separately authorized validation requires it.

## Decision Boundary

No implementation is justified by this review. Keep the frozen PPO, frozen submission, v18 engine, reward logic, Land #4 behavior, checkpoints, and production artifacts unchanged. Any future diagnostic should consume the cached traces first and report baseline reproducibility before claiming a counterfactual effect.

