# 📋 KAGGRICULTURE APEX: OPERATIONAL ROADMAP & TODO

---

## 🔒 1. Current Freeze & Operational State
- 🛡️ **APEX 3.5 PROD (`submission.py`, Ref 55483322)**: Active live on Kaggle. **100% FROZEN & UNTOUCHED**.
- 🚀 **APEX 4.0 (`APEX4_SUBMISSION_FINAL.py`, SHA256 0f3ddc3c...)**: Certified master candidate. **100% FROZEN & RELEASE-READY**.
- 🛡️ **APEX 3.5 Rollback Archive (`APEX35_ROLLBACK_ARCHIVE/`)**: Intact and verified.
- ❌ **APEX 4.1 ML Pipeline**: **INVALIDATED** — all stages used synthetic data, agent stub is broken.
- 🎯 **Target Goal**: **2,000+ Kaggle Skill Rating**.

---

## 🚀 2. Immediate Deployment Actions (Upon User Command)
1. [ ] **Execute Production Cutover**:
   ```powershell
   Copy-Item -Force D:\Kaggriculture\APEX4_SUBMISSION_FINAL.py D:\Kaggriculture\submission.py
   ```
2. [ ] **Verify Production Hash Identity**:
   ```powershell
   Get-FileHash D:\Kaggriculture\submission.py -Algorithm SHA256
   # Must equal: 0F3DDC3C5B67999D51508A38361BAFE140A9050D7E2E3039AE2CCBC810DFF45A
   ```
3. [ ] **Submit `submission.py` to Kaggle Competition**.
4. [ ] **Log New Submission ID & Timestamp in Registry**.

---

## ⚠️ 3. APEX 4.1 ML Branch — What Went Wrong & What To Do Next

### What was broken:
- All 8 training stages generated "game states" using `np.random.randn(batch_size, 256)` — pure noise
- Win/loss outcomes came from logistic formulas (`1/(1+exp(...))`) instead of game simulation
- The GPU engine only modeled milk/wool production (no crops, workers, grid, or pathfinding)
- Parity validators hardcoded `"PASS"` without running `kaggle_environments`
- The packaged submission returns `{"action": "APEX41_EXECUTE"}` — crashes immediately

### Requirements for a valid APEX 4.1 ML pipeline:
1. [ ] **Real game episodes**: Train against `kaggle_environments` or a GPU simulator with verified parity
2. [ ] **Real state features**: Extract 256-dim features from actual `observation` dictionaries
3. [ ] **Real evaluation**: Measure WR/MCV from actual match outcomes, not formulas
4. [ ] **Valid submission format**: Agent must return `{"farmer": [...], "hands": [...], "market": [...]}`
5. [ ] **Genuine parity testing**: Differential test GPU engine against `kaggle_environments` end-to-end
6. [ ] **Honest reporting**: Never hardcode metrics or safety verdicts

---

## 📊 4. Post-Launch Telemetry & The 2,000 Rating Roadmap
1. **Stage 1 (Matches 1–30)**: Ingest initial match telemetry; verify >= 75% WR in the 1000–1200 bracket.
2. **Stage 2 (Matches 30–75)**: Monitor bracket escalation through 1200–1500 tier.
3. **Stage 3 (Rating Wall Identification)**: If win rate drops <55% in higher tiers (e.g. 1600+), isolate the loss archetype.
4. **Stage 4 (APEX 4.1 Targeted Overlay)**: Build a properly validated adaptive rule or ML agent for that specific wall.
