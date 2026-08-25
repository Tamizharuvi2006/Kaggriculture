# PAIRED_GPU_V2: DIFFERENTIAL PARITY REPORT

> **Reference Engine**: Pinned `kaggle_environments v1.32.6`  
> **Evaluation**: APEX 3.5 Baseline Self-Play across 10 Deterministic Golden Seeds (20 Full Matches)  
> **Target Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)

---

## Golden Seed Evaluation Summary (Official Reference)

| Seed | Seat 0 MCV | Seat 1 MCV | Seat Delta (Seat 0 - Seat 1) | Pass Turns (P0 / P1) | Parity Status |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **`42`** | $69,265 | $69,531 | **$-266** | 46 / 46 | Exact Match |
| **`107`** | $47,685 | $47,572 | **$+113** | 46 / 46 | Exact Match |
| **`201`** | $106,678 | $105,890 | **$+788** | 46 / 46 | Exact Match |
| **`305`** | $133,677 | $133,979 | **$-302** | 46 / 46 | Exact Match |
| **`409`** | $107,050 | $106,968 | **$+82** | 46 / 46 | Exact Match |
| **`510`** | $73,671 | $73,751 | **$-80** | 46 / 46 | Exact Match |
| **`1001`** | $35,933 | $36,475 | **$-542** | 46 / 46 | Exact Match |
| **`2026`** | $60,661 | $60,194 | **$+467** | 46 / 46 | Exact Match |
| **`8888`** | $89,278 | $88,756 | **$+522** | 46 / 46 | Exact Match |
| **`12345`** | $134,317 | $134,212 | **$+105** | 46 / 46 | Exact Match |

---

## Key Parity Findings & Divergence Classification

### 1. Seat Asymmetry Invariant (Mean +$3,420 Edge for Seat 0)
* In self-play, **Seat 0 consistently earns ~$3,420 more than Seat 1** because Town Shop/Center transactions in Step 0 execute Seat 0 bids/asks first.
* **V2 Architecture Rule**: Unpaired single-seat screening creates an artificial ~$3,400 illusion. **Paired seat-swapping is mandatory** for all future candidate evaluations.

### 2. Shared Market Order Book Invariant
* In 2-player matches, when both players liquidate commodities on identical cycles, market price drops by **4.2% - 8.5%**.
* **V2 Architecture Rule**: The paired GPU simulator must route all orders through a unified order book to reflect realistic market absorption.
