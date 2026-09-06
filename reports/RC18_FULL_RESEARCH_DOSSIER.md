# Kaggriculture RC16–RC18 Full Research Dossier

**Date**: 2026-09-06  
**Branch**: `arena/01a0761d-kaggriculture`  
**Production file**: `submission.py` = **RC18**  
**Simulator**: `kaggle_environments` 1.32.7, `episodeSteps=720`, `townCenterSellInterval=24`, `shedCapacity=100`  
**Eval rule**: official interpreter only. Paired seat-swap. `ProcessPoolExecutor(max_workers=10)`.  
**This document is the session of record.** Shorter notes live in `RC17_ORDER_PRIORITY_REPORT.md` and `RC18_CEILING_PIPELINE_REPORT.md`.

---

## 0. Why the project kept failing

Live Kaggle TrueSkill is **binary W/L**. A −$419 loss costs the same Elo as a −$24,000 loss.

Across APEX, D.1, PPO, and RC1–RC15 the same loop repeated:

1. Local / solo / open-loop tests look strong (60–100% WR, “$150k engine”).
2. Official **paired shared-market** tests collapse to **~50% WR / ~$0**.
3. A markdown file declares a frozen champion.
4. Live rating falls. Another overlay is stacked.

Concrete historical proof:

| Cycle | Local claim | Official paired / live |
|---|---|---|
| EXP-0113–0120 (8 GPU candidates) | 58–100% WR | **exactly 50% WR, +$0** |
| V8.3 | 100% local WR | live **816** Elo, rolled back |
| APEX 4.1 ML | “trained pipeline” | `np.random.randn` states; invalid action format |
| RC16 (this session) | finish 12-animal herd | **50% WR, −$1,031** |
| V4.1 / v18 | — | **best live rating (1714 converged)** |

Physical production (3 lands, ~38–40 strawberries, cows, 11–13 workers) is **already at the tile cap**. High-MCV and low-MCV traces have the same asset counts. Remaining variance is **shared-market realization**.

Do not repeat: Land #4, 14th worker, 5th strawberry wave, trickle-sell 1u, hold milk/straw for a price, unilateral batch caps, PPO action overrides, 1-step wrappers, synthetic-data ML, Day-29 labor cuts, 50+ carrots, town-wheat denial, solo GPU screens, open-loop replay as proof.

---

## 1. Engine ground truth (from `kaggriculture.py`, not old D.1 docs)

### Time

- 720 steps = 30 days × 24 hours. `day = step // 24` is **0-indexed**. Last full day is **day 29, hour 23**.
- Town center consumes once per day (`townCenterSellInterval=24`).
- Town shops consume every 4 turns. Max 8 shop instances.

### Crops

| Crop | Seed | First yield | Interval | Held cap | Ongoing? |
|---|---:|---:|---:|---:|---|
| Wheat | $10 | day 2 | — | 6 | no |
| Carrot | $20 | day 2 | — | 4 | no |
| Tomato | $50 | day 8 | 1 | 4 events | yes |
| **Strawberry** | $100 | **day 10** | **2** | **4 events then weed** | **yes** |
| Melon | $80 | day 10 | — | 6 | no |

Strawberry production ticks at ages **10, 12, 14, 16**. Each tick adds **+1**, or **+2 if watered that day and fertilized**. Held cap is 4, so you **must harvest between ticks** or fertilizer is wasted. After the 4th tick the plant gets a lifespan and decays to a weed.

Two consecutive unwatered days → weed. Planting day counts as unwatered.

### Animals

| Animal | Cost | First yield | Interval | Held cap | Product |
|---|---:|---:|---:|---:|---|
| Cow | $400 | **day 8** | 2 | 6 | Milk $160 |
| Sheep | $500 | day 6 | 3 | 6 | Wool $200 |
| Goose | $300 | day 4 | 1 | 4 | Egg $50 |

CARE banks +1 per fed+cared day, paid on the next fed production. Two unfed days → animal deleted, pasture remains.

### Market

- Max **10 orders per player per turn**. Extra dropped.
- Interleaved **unit-by-unit lockstep**. Slot 0 of both players quotes on the same inventory.
- `SELL` at $1 does **not** add supply.
- Strawberry `T=100`, linear glut: ~65 extra units can send price $120 → $1.
- Milk `T=122`, linear glut.
- Wheat is log-damped (almost uncrashable).
- Shed capacity **100**. End-of-day backpack overflow is **deleted**.

### Labor

Hands expire every midnight. Fibonacci hire costs: 1,1,2,3,5,8,13,21,34,55,89,144. Twelve hires ≈ $376 wages. One strawberry harvest of 4u at $150 is $600.

---

## 2. What $150k actually is (Phase 82–85 + this session)

Two orthogonal dimensions:

```
Terminal wealth ≈ (seed town demand pie) × (our capture share)
```

| Regime | Pie | Capture | Typical our score |
|---|---:|---:|---:|
| Saturated peer duopoly | ~$160k | ~50% | **~$80k** |
| Elite high-demand duopoly | ~$270–300k | ~50% | **~$135–150k each** |
| Weak / bankrupt opponent | ~$170k | ~90–100% | **~$150–174k** |

Phase 84 factorial: **97.3%** of the $150k “elite gap” is opponent weakness, **2.0%** seed demand, **1.6%** interaction.

You cannot force $150k on a $130k pie by holding inventory. Phase 62: crash-avoidance → 18% WR, −$6.6k. Milk-hold → −$17k. Unilateral batch caps → opponent takes ~62% of the pie.

**Measured monopoly (vs `pass`, 8 seeds, official sim):**

| Bot | Mean | Max | Min | ≥$150k | ≥$100k | Straw sold |
|---|---:|---:|---:|---:|---:|---:|
| RC17 | $95,692 | $106,617 | $73,742 | 0/8 | 4/8 | 150 |
| RC18 | $115,205 | $138,148 | $92,132 | 0/8 | 6/8 | 285 |
| **v18 / V4.1** | $133,833 | **$173,830** | $54,072 | **4/8** | 7/8 | **616** |

v18 always sells **616 strawberries and 689 milk** vs pass (deterministic saturated pipeline). That is the only bot we measured over $150k.

---

## 3. Forensic: why RC15/RC17 maxed at ~$86–107k

### 3.1 Day-8 liquidity canyon (100% of 40 self-play seats)

Day 8 cash $57–$100. Day 10 cash <$200 on 37/40 seats. Cannot buy a $400 cow. Then RC15’s “armored horizon gate” (`day > 10 and opp_money > 8000: break`) **freezes the herd in peer games**, which is exactly when rating is decided.

Planned herd: 8 cows + 4 sheep = 12. Actual RC15 self-play: mean **6.75** animals (max 8).

### 3.2 Day-29 hire=6 is not the leak on this chassis

By day 28, yield is already 0 and the shed is empty. Hiring 6 vs 12 on day 29 does not explain the $150k gap. RC3-D (hire 0 on day 29) was catastrophic on a different chassis; do not re-open it as the main theory here.

### 3.3 Slot-0 fertilizer (the coin-flip leak)

Dawn dumps (`hour == 1`) fill the 10-order cap. On seed 42, first SELL item:

- FERTILIZER 23 times
- MILK 5
- WOOL 3
- MELON 2
- STRAWBERRY 2

The book is interleaved. $40–$50 fertilizer was clearing **before** milk/strawberry. That is the razor-thin (−$419 to −$3,500) TrueSkill leak.

### 3.4 Strawberry plants were not realized

RC vs pass, seed 100, peak **39** strawberry tiles — same as v18’s **40**. Sold units:

| | Straw units | Milk units | Final $ |
|---|---:|---:|---:|
| RC17 | 147 | 144 | $105,058 |
| v18 | 616 | 689 | $156,179 |

RC17 only created water tasks if `consecutive_unwatered >= 1` **or** `hour >= 16`. Ongoing strawberries were left dry until late afternoon, then weeded after one harvest. Harvest threshold 3 capped fertilizer. Opening plan locked **9 melon tiles** until melon LTV died, so those tiles never became a strawberry generation.

147 / 39 ≈ **3.8 units/plant** = one harvest. Theoretical fertilized two-generation pipeline ≈ 16 units/plant × 40 ≈ 640, matching v18’s 616.

---

## 4. Session experiments

All numbers below are **official** `kaggle_environments` 1.32.7. No GPU solo screens. No open-loop tapes.

### Artifact hashes (SHA-256)

| File | Bytes | SHA-256 | Role |
|---|---:|---|---|
| `submission_rc15.py` | 55,569 | `525fb7d17c7ed960…fc2aa761` | Frozen pre-session production |
| `submission_rc16.py` | 55,497 | `83d4db755be7eac7…be87ca46e0` | **FALSIFIED** extra-animal freeze removal |
| `submission_rc17.py` | 56,183 | `dd658304622a99f3…e9df4f` | Slot-0 sell priority |
| `submission_rc18.py` | 56,440 | `0c88ba7bb3c523ad…8dfda0` | Strawberry realization pipeline |
| `submission.py` | 56,440 | `0c88ba7bb3c523ad…8dfda0` | **Live candidate = RC18** |

Rollback:

```bash
cp submission_rc17.py submission.py   # order-priority only
cp submission_rc15.py submission.py   # pre-session RC15
```

---

### RC16 — FALSIFIED (do not promote)

**Hypothesis**: RC15’s `if day > 10 and opp_money > 8000: break` stops the planned 8c/4s herd in peer games. Removing it completes livestock and wins coin-flips.

**Change**: delete the armored horizon gate only. Payback gate (`remaining_days < 7` and `payback + 3`) kept.

**Paired vs RC15** (30 seeds × 2 seats = 60 matches, start seed 2000, stride 137):

| Metric | Value |
|---|---|
| Record | **30–30** |
| WR | **50.0%** |
| Mean Δ | **−$1,031** |
| Median Δ | −$94 |
| Mean animals | 11.57 vs 8.67 |
| Mean cows / sheep | 7.67 / 3.90 |
| p05 Δ | −$7,872 |
| Worst | −$18,087 (seed 4055, both seats, 12 animals vs 7) |

Seat 0: 16W, −$1,196. Seat 1: 14W, −$866. Seed split: 10 both-win, 10 both-loss, 10 split.

**Verdict**: more milk into a shared book. Opponent captures the preserved price. Classic EXP-0113–0120 failure. File kept as evidence only.

---

### RC17 — PROMOTED (then superseded by RC18)

**Hypothesis**: fertilizer in slot 0 loses the interleaved milk/strawberry race. Reorder sells. Same farm, same quantities.

**Change** (only `_market_orders` sell assembly):

```
MILK → STRAWBERRY → WOOL → MELON → tomato/carrot/egg → FERTILIZER → wheat surplus
```

Verified on seed 42 dawn dumps: D9 slot 0 is now `SELL MILK 18`, not fertilizer.

**Paired vs RC15** (official, 10 workers):

| Suite | Seeds | Matches | W–L | WR | Mean Δ | Median Δ |
|---|---:|---:|---|---:|---:|---:|
| Discovery (seed 2000 ×137) | 30 | 60 | **41–19** | **68.3%** | **+$1,696** | **+$2,176** |
| Holdout (seed 9000 ×137) | 30 | 60 | **37–23** | **61.7%** | **+$943** | **+$1,960** |
| **Combined** | **60** | **120** | **78–42** | **65.0%** | **+$1,320** | — |

Discovery seats: 21/30 and 20/30. Both-win seeds 17 vs both-loss 6. One-sided binomial P(W≥41 | p=0.5) ≈ **0.003**.

Razor band `|Δ| < $3,500`: **16 wins vs 7 losses**. That is the TrueSkill band.

**vs v18** (10 seeds × 2 seats = 20): RC15 **0–20**, mean Δ −$53,009. RC17 **0–20**, mean Δ −$50,575. Both destroyed. Do not claim 1700 Elo.

---

### RC18 — CURRENT PRODUCTION

**Hypothesis**: RC plants ~40 strawberries but sells ~150 units because they are not watered/harvested/converted. Fix the realization pipeline. Keep RC17 slot-0 order.

**Changes:**

1. Water **every** unwatered crop from dawn. Ongoing strawberries at priority 2. Urgent (already missed a day, or hour ≥ 18) at priority 0. Skip watering on day 29 (harvest/drop only).
2. `ongoing_harvest_threshold`: 3 → **1** so fertilizer +2/tick is not held-capped.
3. `crop_transition_day`: 5 → **3**. `strawberry_last_plant`: 18 → **19**.
4. Retain opening melon tiles only while `day < 12`. After that those 9 NW tiles become strawberries so a 4-yield generation still finishes.
5. `COLLECT_FERTILIZER` priority 4 → **2**, EV `p_fert * 1.5`.
6. `_hire_target` returns **12 on day 29** (was 6). Last-day harvest/drop crew.

**Monopoly vs `pass` (8 seeds 100, 117, …):**

| Bot | Mean | Max | Min | ≥$150k | ≥$100k | Straw sold mean |
|---|---:|---:|---:|---:|---:|---:|
| RC17 | $95,692 | $106,617 | $73,742 | 0 | 4 | 150 |
| **RC18** | **$115,205** | **$138,148** | **$92,132** | **0** | **6** | **285** |
| v18 | $133,833 | $173,830 | $54,072 | **4** | 7 | 616 |

RC18 closed about **half** of the monopoly gap to v18 ($106k → $138k toward $174k). **Still not $150k.**

**Paired vs RC17** (15 seeds × 2 seats = 30 matches, start 4000, stride 131):

```
RC18 30–0 vs RC17
mean Δ     +$17,029
mean RC18  $81,939
mean RC17  $64,910
max RC18   $108,184   (shared pie — not a monopoly ceiling)
max RC17   $ 87,008
```

**vs v18** (6-seed probe, RC18 seat 0):

| Seed | RC18 | v18 | Δ |
|---:|---:|---:|---:|
| 42 | $44,286 | $50,789 | −$6,503 |
| 100 | $42,740 | $67,928 | −$25,188 |
| 117 | $66,094 | $90,333 | −$24,239 |
| 200 | $79,574 | $117,236 | −$37,662 |
| 300 | $51,352 | $54,702 | −$3,350 |
| 400 | $75,839 | $104,513 | −$28,674 |

**0–6**. v18’s second strawberry generation is still the $150k machine.

---

## 5. Seed-100 monopoly waterfall (RC17 vs v18)

Same seed, vs `pass`. Illustrates the harvest gap with prices still high.

| Day | RC17 straw / cows / $ | v18 straw / cows / $ |
|---|---|---|
| D00 | 0 / 3 / $771 | 0 / 3 / $29 |
| D08 | 15 / 3 / $97 | 12 / 5 / $1,240 |
| D12 | 39 / 8 / $9,236 | 33 / 8 / $15,432 |
| D16 | 39 / 8 / $12,668 | 40 / 8 / $28,827 |
| D20 | 39 / 8 / $25,648 | 40 / 8 / $60,576 |
| D24 | 26 / 8 / $61,007 | 34 / 8 / $96,847 |
| D28 | 9 / 7 / $90,397 | 12 / 8 / $137,837 |
| Final | **$105,058** | **$156,179** |

Sell-side (action qty × quoted price; v18 may over-request, money is the ground truth):

| Item | RC17 units / $ | v18 units / $ |
|---|---|---|
| Strawberry | 147 / $38,989 @ $265 | 616 / $141,365 @ $230 |
| Milk | 144 / $35,446 @ $246 | 689 / $186,796 @ $271 |
| Melon | 114 / $25,368 | 224 / $50,588 |
| Wool | 61 / $14,441 | 373 / $15,831 |
| Fertilizer | 139 / $11,821 | 443 / $33,744 |
| Wheat | 33 / $1,147 | 1,106 / $48,660 |

RC17’s 39 tiles produced like **one** harvest. v18’s 40 tiles produced like **two fertilized generations**.

---

## 6. What would actually cross $150k

Copy v18’s pipeline, nothing else:

1. First strawberry ~day 4 (not day 8–12).
2. Finish generation 1 ~day 16–18 (4 ticks).
3. DIG weed → replant immediately (generation 2 still gets 2–4 ticks before day 29).
4. Fertilize every tick and **harvest every tick** so +2 is not held-capped at 4.
5. Keep 12 workers through day 28–29.
6. Do not add Land #4, late cows, milk-holds, or PPO.

Math: 40 tiles × 2 generations × 4 ticks × 2 fertilized units ≈ **640 units**. v18 measured **616**. At monopoly strawberry prices $220–$280 that is $135k–$180k from strawberries alone, plus milk.

RC18 is generation-1 realization only (285 units). Generation 2 is the remaining $150k gap.

---

## 7. How to judge live rating after submit

Kaggle Elo ignores coin margin. Watch:

1. **W/L on games decided by <$3,500.** RC17 already flipped that band 16–7 vs RC15. RC18 should keep it and add production vs weak bots.
2. **Monopoly / weak-opponent scores.** If live max stays ~$90k, generation 2 is still missing. If live max enters $120k–$140k, RC18 is working. If live max enters $150k+, v18-parity harvests landed.
3. **Do not** read mean wealth vs v18-like peers (~$80k) as a regression.

Submit `submission.py` (RC18). Only the latest two submissions stay in matchmaking. Do not upload RC16.

---

## 8. Reproduction

```bash
python3 -m venv /tmp/kagvenv
/tmp/kagvenv/bin/pip install 'kaggle-environments>=1.32.7'

# paired RC17 vs RC15 (holdout)
/tmp/kagvenv/bin/python experiments/eval_rc17_paired.py --seeds 30 --start-seed 9000 --workers 10

# monopoly ceiling
/tmp/kagvenv/bin/python -c "
import kaggle_environments as ke
env=ke.make('kaggriculture', configuration={'episodeSteps':720,'seed':100})
res=env.run(['submission.py','pass'])
print(res[-1][0]['observation']['farms'][0]['money'])
"
```

JSON evidence:

- `reports/RC16_PAIRED_VS_RC15.json`
- `reports/RC17_HOLDOUT_VS_RC15.json`
- `reports/RC17_VS_V18.json`
- `reports/RC18_CEILING_PIPELINE_REPORT.md`
- this file

Eval helpers:

- `experiments/eval_rc16_paired.py`
- `experiments/eval_rc17_paired.py`

---

## 9. Decision log

| ID | Hypothesis | Gate | Decision |
|---|---|---|---|
| RC16 | Remove Day-10 rich-opponent animal freeze | 60 paired vs RC15: 50% WR, −$1,031, 11.6 animals | **FALSIFIED** |
| RC17 | Slot-0 milk/strawberry before fertilizer | 120 paired vs RC15: 65% WR, +$1,320 | **PROMOTED**, then stacked into RC18 |
| RC18 | Dawn water + harvest-1 + one melon cycle + day-29×12 | 30 paired vs RC17: **30–0**, +$17k; monopoly max $138k | **CURRENT PRODUCTION** |
| $150k | Need two strawberry generations like v18 | RC18 0/8 ≥$150k; v18 4/8, max $173,830 | **NOT YET — next isolated experiment only** |

---

## 10. One-page submit card

```
File:     submission.py
Identity: RC18 = RC17 slot-0 sells + strawberry realization pipeline
SHA-256:  0c88ba7bb3c523ad4e8ab199fbfbf2b04a3d0fcf6cfcfbe03410fc7ce58dfda0
Size:     56,440 bytes
vs RC15:  RC17 layer 78–42 / 120 (65.0%)
vs RC17:  RC18 layer 30–0 / 30 (+$17,029)
vs pass:  mean $115k, max $138k, 0×$150k (v18 max $174k, 4×$150k)
vs v18:   still loses; do not claim 1700 Elo
Rollback: cp submission_rc17.py submission.py
```
