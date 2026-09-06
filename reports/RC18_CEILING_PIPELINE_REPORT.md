# RC18: Realize planted strawberries (ceiling step toward $150k)

**Date**: 2026-09-06  
**Control**: RC17 (`submission_rc17.py`)  
**Candidate**: RC18 (`submission_rc18.py` → `submission.py`)  
**Simulator**: `kaggle_environments` 1.32.7, 720 steps, `townCenterSellInterval=24`

## What $150k actually is

Reports (Phase 82–85) and live physics agree:

- You do **not** mint $150k by dumping more into a peer duopoly (~$80k each).
- **$150k+ happens vs a weak opponent** (uncrowded prices) or as a 50/50 split of a ~$270k elite pie.
- V4.1 / `kaitofukami-v18` already does this: **4/8 monopoly seeds ≥ $150k, max $173,830**.
- RC17 monopoly: **0/8 ≥ $150k, max $106,617**. Same ~40 strawberry plots. The gap is **harvests, not tiles**.

Engine ground truth (not the old D.1 docs):

- Strawberry yields **4 times** (ages 10/12/14/16), **+1 unit/tick** or **+2 if watered+fertilized**, then weeds.
- Two missed waters → weed.
- Cow first milk is **day 8**, then every 2 days.

RC17 only created water tasks after a missed day or after hour 16, harvested at 3 units (capping fertilizer), and replanted melon on 9 NW tiles until late. Result vs pass: **147 strawberries sold vs v18’s 616**.

## RC18 changes (one pipeline: keep plants alive and convert them to cash)

1. Water every unwatered crop from dawn (ongoing straw at priority 2).
2. Harvest ongoing crops at **1 unit** so fertilizer bonus is not capped.
3. Start cash-crop plan on **day 3**; strawberry last plant **day 19**.
4. **One melon cycle only** — after day 12 those 9 tiles become strawberries.
5. Collect fertilizer at priority 2.
6. Keep **12 workers on day 29** (last harvest/drop).

RC17 slot-0 sell order is unchanged.

## Official results

### Monopoly vs `pass` (ceiling)

| Bot | n | Mean | Max | Min | ≥$150k | ≥$100k | Straw sold |
|---|---:|---:|---:|---:|---:|---:|---:|
| RC17 | 8 | $95,692 | $106,617 | $73,742 | **0** | 4 | 150 |
| **RC18** | 8 | **$115,205** | **$138,148** | **$92,132** | **0** | **6** | **285** |
| v18 | 8 | $133,833 | **$173,830** | $54,072 | **4** | 7 | 616 |

RC18 does **not** yet clear $150k. It closed about **half** the monopoly gap vs v18 ($106k → $138k toward $174k).

### Paired vs RC17 (do not give back W/L)

15 seeds × 2 seats = 30 matches:

**RC18 30–0 vs RC17**, mean **+$17,029**, mean wealth $81,939 vs $64,910.

### vs v18 (still behind)

0–6 on a 6-seed probe. v18’s second strawberry generation + full fert cycle is still the $150k machine.

## Rollback

```bash
cp submission_rc17.py submission.py   # order-priority only
cp submission_rc15.py submission.py   # pre-RC17
```

## What would actually cross $150k

Copy v18’s **two-generation** strawberry+fertilizer pipeline (first plant ~day 4, finish gen-1 ~day 16–18, replant, 616 units). Do not add Land #4, extra late cows, or milk-holds. Those were already falsified.

Do not judge RC18 on peer self-play max (~$108k). That pie is shared. Judge monopoly max and live W/L vs weak/mid bots.
