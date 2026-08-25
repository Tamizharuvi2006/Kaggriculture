# 🛡️ EXP-0130: PHASE 1 FORENSIC VALIDATION REPORT

> **Target Hypothesis**: `EXP-0130` (`LATE_GAME_SEED_WASTE_CUTOFF`)  
> **Variable Family**: `Capital_Preservation`  
> **Sample Population**: Decompressed APEX 3.5 Production Action Schedule (719 Steps) & 807 Match Trajectories

---

## 🔍 1. Forensic Discovery: Zero Late-Game Seed Purchases in Baseline

```
========================================================================================================
[EMPIRICAL SCHEDULE AUDIT: ALL 719 STEPS OF APEX 3.5 PROD]
========================================================================================================
  • Last STRAWBERRY Seed Purchase : Step 335 (Day 13, Hour 23)
  • Last Seed Purchase of Any Crop: Step 383 (Day 15, Hour 23 - Wheat Seed)
  • Total Seed Purchases Post-624 : 0 Units ($0.00)
  • Total Seed Purchases Post-672 : 0 Units ($0.00)
  • Post-672 Market Activity      : Exclusively `BUY_PRODUCT WHEAT` for cow feed
  • Cow Milk Feed Economics       : 1 Wheat ($15) --> 1 Milk ($160) every 6 hours (High Positive ROI)
========================================================================================================
```

---

## 🔬 2. Causal Disentanglement: The Theoretical vs Realized Gap

```text
THEORETICAL HYPOTHESIS:
"Bot plants strawberries at Step 680 --> Strawberries take 48h --> Unharvested at Step 720 --> -$1,320 wasted."

EMPIRICAL REALITY FROM DECODED BASELINE SCHEDULE:
"APEX 3.5 PROD stops buying all crop seeds at Step 383.
From Step 384 to 719, APEX operates as a pure livestock/milk engine.
Actual post-672 seed waste = EXACTLY $0.00."
```

* **Why Post-672 Wheat Purchases Cannot Be Cut**:
  - The only purchases occurring in Steps 672–718 are `BUY_PRODUCT, WHEAT` (e.g. Step 673: 15 units, Step 675: 13 units).
  - These wheat units feed cows at steps 678, 684, 690, 696, 702, 708, 714, 720.
  - Cutting wheat feed would starve cows, destroying ~$3,500+ in late-game milk revenue.

---

## ⚖️ 3. Formal Governance Verdict: `INVALID_MECHANISM`

* **Contract Enforced**: Because APEX 3.5 PROD has **zero seed expenditure after Step 383**, the proposed late-game cutoff provides **$0.00 realized edge**.
* **Zero Compute Waste**: In accordance with research governance, **`EXP-0130` is formally classified as `INVALID_MECHANISM`** and aborted before GPU screening.
* **Production Safety**: `submission.py` remains 100% frozen.
