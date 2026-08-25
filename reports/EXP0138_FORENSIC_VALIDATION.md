# 🔬 EXP-0138: PHASE 1 FORENSIC & SPATIAL INFRASTRUCTURE REPORT

> **Target Hypothesis**: `EXP-0138` (`PASTURE_2_EXPANSION_PACING`)  
> **Variable Family**: `Spatial_Infrastructure`  
> **Evaluation Window**: Steps 170 – 275 (Day 7 to Day 11) of APEX 3.5 Production Schedule

---

## 📊 1. Schedule Infrastructure & Transport Audit

```
========================================================================================================
[PASTURE 2 INFRASTRUCTURE & ANIMAL TRANSPORT AUDIT: STEPS 170 - 275]
========================================================================================================
  • Land 2 Expansion Executed     : Step 170 (Unlocks SW Quadrant)
  • Sheep Purchases               : Step 196 (2 Sheep) & Step 201 (2 Sheep) = 4 Sheep in Shed
  • Baseline Pasture 2 Build Step : Step 260 (Day 10.8)
  • First Worker PICKUP from Shed : Step 261 (Day 10.9)
  • First Worker PLACE in Pasture2: Step 264 (Day 11.0)
  • Interim Worker Activities     : Steps 171–259: 100% committed to Strawberry Watering & Fertilizing
========================================================================================================
```

---

## 🔍 2. Identification of the Binding Constraint

```text
THE NAIVE HYPOTHESIS:
"Build Pasture 2 at Step 175 --> Place Sheep 80 steps earlier --> +2 Shearing Cycles (+$1,400 MCV)."

THE PHYSICAL REALITY IN THE OPEN-LOOP SCHEDULE:
1. In APEX 3.5's fixed schedule, worker hands are 100% scheduled for strawberry watering and 
   fertilizer harvesting between Steps 171 and 259.
2. The worker transport sequence (['PICKUP', 'SHEEP'] and ['PLACE', 'SHEEP']) is hardcoded at Steps 261–268.
3. Accelerating the BUILD_PASTURE action to Step 175 creates an empty pasture, but the sheep sit in the 
   shed until Step 261 anyway because no worker is allocated to transport them before Step 261.
4. An isolated infrastructure shift produces EXACT PARITY (50.0% WR / +$0 MCV) on Official Gate 1.
```

---

## ⚖️ 3. Formal Verdict: `INVALID_MECHANISM`
In accordance with our physical binding constraint protocol, `EXP-0138` is **classified as `INVALID_MECHANISM`** and aborted before GPU screening. Zero GPU compute wasted.
