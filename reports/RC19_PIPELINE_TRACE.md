# RC19 pipeline trace — two-generation strawberries are not v18's $150k engine

Production remains **RC18**. `submission.py` is unchanged. `submission_rc19.py` is an unpromoted experiment.

## What v18 actually does (seed 100 vs pass)

Official-sim tracer, seed 100, vs `PASS`:

| | money | unique straw tiles | plant days | SELL requested straw | **market-cleared straw** | wheat cleared | melon | milk |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| RC18 | $132301 | 45 | 3–13 (wave of 21 on D9) | 285 | **189** | 22 | 65 | 112 |
| v18  | $156179 | **40** | 4–14, **no replant** | 616 | **240** | **674** | 117 | 191 |

- v18 `plant_events=40 unique_tiles=40`. One generation. The historical **616** figure is over-requested `SELL` quantity, not harvested/cleared units.
- Naive two-gen arithmetic (40×6 ticks×2 fert=480) was never v18's ledger.
- NE/SW land unlocks D6/D9. A strawberry planted D7+ finishes ~D23 and cannot complete a useful second generation before EOD 28.
- v18's extra wealth on this seed is **wheat (674 vs 22)**, **second melon cycle (117 vs 65)**, and **milk (191 vs 112)** — not a second strawberry generation.

Daily snapshot (v18): strawberries stay ~40 through D20, then 31–32 **wheat** tiles appear D26–27 as strawberries age out. RC18 instead accumulates 44 weeds after `last_plant` because DIG was gated on `day <= last_plant(crop)`.

## RC19 experiment (observation-driven rotation, not a tape)

On the RC18 chassis:

1. Keep opening melon tiles through D22 (two melon cycles; melon `last_plant=16`).
2. After `strawberry_last_plant` (19), rewrite strawberry plan tiles to wheat.
3. DIG weeds always; DIG spent ongoing plants (`max_lifespan_step>=0` / strawberry age≥16).
4. Loosen wheat shed buffer to `animal_count+3`.
5. Feed is always prio 0 so rotation DIG cannot starve the herd (a high-EV DIG variant killed cows and dropped seed 100 to $129k / 57 milk).

### vs pass, 8 monopoly seeds

| seed | RC19 $ | straw | wheat | melon | milk |
|---:|---:|---:|---:|---:|---:|
| 100 | 146139 | 148 | 26 | 95 | 105 |
| 101 | 139325 | 141 | 27 | 107 | 95 |
| 102 | 100754 | 154 | 24 | 106 | 129 |
| 103 | **82353** | 214 | 24 | 104 | 95 |
| 200 | 129899 | 157 | 31 | 113 | 124 |
| 201 | 128410 | 182 | 22 | 105 | 127 |
| 202 | 146084 | 162 | 22 | 91 | 98 |
| 203 | 137553 | 174 | 22 | 102 | 80 |
| **MEAN** | **126315** | | | | |
| MAX | 146139 | | | | |
| n≥150k | **0/8** | | | | |

RC18 monopoly reference (same seeds): mean **115205**, max **138148**, 0≥150k.

Melon two-cycle worked (cleared ~100 vs RC18 ~65). Wheat rotation **did not** (22–31 cleared, not 674): living D9 strawberries are still producing through D24, which is also wheat `last_plant`. Weeds from D3–D5 plants appear in time, but watering EV still crowds DIG/plant on most hours.

Paired RC19 vs RC18 (first RC19 eval, before feed-prio fix): **2–6**. Floor on seed 103 is broken.

### Isolated CARE prio 0 on RC18

Milk rose on some seeds; mean **fell** to $113149 (straw harvest labor stolen). Not adopted.

## Decisions

- Do **not** replace `submission.py` with RC19.
- Do **not** copy the v18 tape.
- Do **not** treat 616 requested strawberries as a production target.
- Two-gen strawberry remains physically available only on early NW tiles (~6–12) and is not the $150k gap.
- Next isolated levers that still match evidence: make wheat rotation win the labor auction **after** water/feed/harvest (hour-gated), without sacrificing remaining strawberry ticks before they are spent; close the milk gap without new cows (CARE that does not starve harvest). Do not add cows, Land #4, or late livestock.
