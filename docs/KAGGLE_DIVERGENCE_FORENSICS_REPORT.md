# 🔬 PHASE 10: KAGGLE DIVERGENCE FORENSICS REPORT

Analyzed 5 trajectory seeds under `townCenterSellInterval = 24` rules.

## 1. First Divergence Step Breakdown:
- **Seed 777001**: Step `107` (Day `4`) | Cash: `$341.00` | Divergent Market Order: `[['SELL', 'WHEAT', 1]]`
- **Seed 777005**: Step `107` (Day `4`) | Cash: `$341.00` | Divergent Market Order: `[['SELL', 'WHEAT', 1]]`
- **Seed 777010**: Step `107` (Day `4`) | Cash: `$341.00` | Divergent Market Order: `[['SELL', 'WHEAT', 1]]`
- **Seed 666001**: Step `107` (Day `4`) | Cash: `$341.00` | Divergent Market Order: `[['SELL', 'WHEAT', 1]]`
- **Seed 590244349**: Step `107` (Day `4`) | Cash: `$341.00` | Divergent Market Order: `[['SELL', 'WHEAT', 1]]`

## 2. Root Cause Diagnostic:
- **Divergence Mechanism**: APEX policy injects extra `SELL` orders during early/mid-game windows (Step 100-250).
- **Town Center Clearance Lag**: Under `townCenterSellInterval = 24`, early crop sales lock market slots for 24 steps, suppressing downstream crop prices when major harvest batches arrive.
