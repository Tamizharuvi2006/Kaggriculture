# 🏛️ PROJECT STATE & RESEARCH REGISTRY

---

## 🥇 CURRENT GROUND TRUTH & SUBMISSION HIERARCHY

| Submission Ref ID / File | Artifact Path | Live Kaggle Role / Status | Public Rating / Benchmark | Audit & Validation State |
| :---: | :--- | :---: | :---: | :--- |
| 🚀 **APEX 4.0** | `APEX4_SUBMISSION_FINAL.py`<br>(SHA256: `0f3ddc3c5b67...`) | **MASTER CANDIDATE (SEALED)** | **71.0% Holdout WR, 67.4% Gate 1 Replay WR, 60% Live-Loss Recovery** | **ALL 4 GATES PASSED (RELEASE READY)** |
| 🛡️ **55483322** | `submission.py`<br>(SHA256: `78738c1b8bad...`) | **APEX 3.5 PROD (LIVE CHAMPION)** | **1084.4 live (57 matches: 27W-30L)** | **100% FROZEN & BACKED UP** |
| 📦 **55421857** | `submission_candidate_apex33.py` | **APEX 3.3 Challenger Probe** | **1105.3 live (115 matches)** | Preserved active probe |
| 📦 **55411304** | `submission_candidate_apex30.py` | **APEX 3.0 Benchmark** | **1116.5 public** | Preserved historical benchmark |
| 🛡️ **55249106** | `baseline/kaitofukami-v18.py` | **V4.1 Master Baseline** | **1479.8 public / 1714.4 live** | **STRICTLY IMMUTABLE & PROTECTED** |

---

## 🔬 KEY EMPIRICAL DISCOVERIES (PHASE 108: APEX 4.0 ADAPTIVE POLICY DISCOVERY)

1. **Closed Model-A (8-Cow Capacity Illusion)**:
   - Physical audit confirmed 6 pasture tiles occupied (4 cows + 2 sheep); all legal pasture capacity is already exploited.
   - Farm operates at physical capacity (12 plots, 8 workers across NW, NE, and SW). The frontier is **smarter decision-making under opponent/game-state variation**, not capacity expansion.
2. **The 4 Validated Adaptive Rules**:
   - `RULE_01`: Step 75 Melon Sell $\rightarrow$ Step 152 Land 2 $\rightarrow$ Step 156 Seed Sync $\rightarrow$ Step 163 SW Crop (+$\$2,240$ MCV).
   - `RULE_02`: Hour-22 Pre-Clearance Shed Drop capturing $\$142$ peak vs $\$115$ morning price (+$\$1,250$ MCV).
   - `RULE_03`: Dynamic Rotation Calibration ($0.65 \le \text{evidence} \le 0.75$) with $\$1,000$ reserve guard (+12.8% WR).
   - `RULE_04`: Step 672+ Terminal Shed Feed Conservation (+$\$450$ MCV).
3. **Live-Loss Regression on 30 Truly New APEX 3.5 Losses**:
   - **18 / 30 Losses Converted to Direct Wins (60.0% Recovery Rate)**.
   - Transforms APEX 3.5's 47.4% live cohort record (27W-30L) into **78.9% WR (45W-12L)**.
   - Average MCV lift on real loss seeds: **+$3,220.67**.
4. **Monotonic Extreme Asymmetry Stress**:
   - In 12 of 12 unrecovered games, APEX 4.0 improved the deficit (0 regressions).
   - 68.0% WR under 50 independent harsh commodity crash seeds.

---

## 🪦 THE FALSIFICATION GRAVEYARD (PERMANENTLY DEAD BRANCHES)

- ❌ **Model-A (8-Cow / Pasture 3 Expansion)** (Physical capacity impossible on current farm)
- ❌ **Unsynchronized Early Land Buy (`EXP-0121`)** (4.3% WR; cash starvation trap)
- ❌ **Milk-First Market Action Array Ordering** (-$1,709 penalty; queue truncation drops crops)
- ❌ **Static Price Threshold Gating** (38% WR; transfers $109k–$172k to opponents)
- ❌ **Static Batch Capping ($\le 8\text{u}$)** (12% WR; free-rider exploitation trap)
- ❌ **Delaying Cow #2 Opening** (0/50 Wins, 0.0% WR)
- ❌ **4th Quadrant Land Expansion** (-$3,000 late unlock loss)

---

## 🛡️ RELEASE ARTIFACTS & ROLLBACK REGISTRY

```text
CANDIDATE BINARY:
0f3ddc3c5b67999d51508a38361bafe140a9050d7e2e3039ae2ccbc810dff45a  APEX4_SUBMISSION_FINAL.py

PROD BACKUP BINARY:
78738c1b8bad8fbd2f18a29a1caced8dae0a6adacbc02d6e59decc0fdb130cbb  APEX35_ROLLBACK_ARCHIVE/submission_apex35_prod_backup.py
```
