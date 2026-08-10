# 🏛️ PROJECT STATE & RESEARCH REGISTRY

---

## 🥇 CURRENT GROUND TRUTH & SUBMISSION STATE

- **Live Kaggle Champion**: V4.1 (`baseline/kaitofukami-v18.py`) — **1714.4 Live Kaggle Rating** (Protected Baseline, Ref `55329352`).
- **Official Candidate Live Submission**: Candidate L+ Standalone ([`generalization_pipeline/submission_candidate_l_plus.py`](file:///D:/kaggriculture/generalization_pipeline/submission_candidate_l_plus.py)).
- **Kaggle Submission Ref**: **`55373438`** (310KB Self-Contained Monolithic Artifact, Submitted Aug 9, 2026).
- **Multi-Archetype Unseen Validation Result**: **100.0% Win Rate SWEEP (100/100 Wins)** across 4 diverse opponent archetypes.
- **Controlled Paired A/B Result**: **20/20 Direct Wins (100.0%)**, +$15,604.60 mean delta ($p = 9.87 \times 10^{-8}$).
- **Randomized Opponent Sanity Result**: **18/20 Wins (90.0%)**, +$12,423.25 mean victory margin.

---

## 🎓 IMPORTANT LESSON FOR SUBAGENT DEVELOPERS

### 🚨 Kaggle Remote Container File Isolation Rule:
- **Problem**: Submission Ref `55373363` (1.7KB wrapper) failed Kaggle validation with `SubmissionStatus.ERROR` because it attempted to import `D:\kaggriculture\baseline\kaitofukami-v18.py` using `importlib.util`. Kaggle executes submissions inside an isolated cloud Linux container where local host file paths do not exist.
- **Solution**: Built `experiments/build_standalone_candidate_l_plus.py`, which embeds the complete 4,448-line strategy core directly into a 310KB self-contained standalone `.py` file (`submission_candidate_l_plus.py`).
- **Verification**: Tested locally with `kaggle_environments` (720 steps), confirmed 0 file dependencies, and re-submitted as Kaggle Ref **`55373438`**.

---

## 🚫 STOP-LISTED PERMANENTLY CLOSED BRANCHES

- ❌ **V8.3 Static Strategy** (816.8 Kaggle Collapse)
- ❌ **V5 Modular Intent Architecture** (0/40 Loss vs V4.1)
- ❌ **Candidate C** (Conditional Cow 9–10 Feed Starvation)
- ❌ **Milk & Crop Inventory Holding / Delayed Sales** ($0.00 Delta)
- ❌ **Forced Second Crop Cycles** (-$20.4k Penalty)
- ❌ **Mid-Game Land Expansion** (-$4.1k Penalty)
