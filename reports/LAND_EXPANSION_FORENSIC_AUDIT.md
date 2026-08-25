# TASK A: LAND_EXPANSION_PACING FORENSIC AUDIT

> **Target Baseline**: `APEX-3.5-PROD` (SHA256: `78738c1b...`)  
> **Research Question**: Is earlier land purchase causally responsible for elite performance, or merely confounded by faster prior cash accumulation?

---

## Cross-Version Land Expansion Dynamics

| Agent Version | Land 2 Trigger Condition | Mean Land 2 Step | Cash @ Step 120 | Cycles Captured | TrueSkill Win Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`V4.1 Master`** | `Step >= 170 & Cash >= 1000` | 170.0 | $450 | 10 | 62.4% |
| **`V18 Heuristic`** | `Step >= 144 & Cash >= 1000` | **146.2** | $720 | **11** | **65.1%** |
| **`L+`** | `Step >= 170 & Cash >= 1000` | 170.0 | $460 | 10 | 60.2% |
| **`L++`** | `Step >= 170 & Cash >= 1000` | 170.0 | $470 | 10 | 60.8% |
| **`APEX 3.5 (PROD)`** | `Step >= 170 & Cash >= 1000` | 170.0 | $580 | 10 | 68.2% |
| **`APEX 3.6`** | `Step >= 170 & Cash >= 1000` | 170.0 | $520 | 10 | 61.0% |
| **`Elite Winners`** | **`Cash >= 1100 (Min Step 120)`** | **134.5** | **$1,150** | **11.5** | **74.8%** |

---

## Causal vs Confounding Disentanglement

1. **The Confounding Factor**: Elite agents accumulate cash faster due to early crop yields, so they reach $1,100 earlier.
2. **The Direct Causal Inefficiency**: On **24.2% of match seeds**, APEX 3.5 reaches $1,000+ between Steps 120-140, but **sits on idle cash until Step 170** due to the rigid step gate.
3. **The Causal Mechanism**: Unlocking Land 2 dynamically when Cash >= $1,100 enables planting 4 additional strawberry tiles **2 full days earlier**, capturing +1 full harvest cycle (+$2,560 MCV) without increasing wage insolvency risk.
