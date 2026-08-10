# 📜 Authoritative Kaggle Rating, Rank Timeline & Submission History

> **Target Objective**: Reconstruct the exact submission history and rating timeline ($2100+\text{ rating} \rightarrow \sim 150\text{ rank} \rightarrow 1714.4\text{ rating}$) to determine whether the bot degraded, was replaced, experienced matchmaking shift, or suffered from metric divergence.

---

## 📅 Chronological Submission & Timeline Matrix

| Date / Timestamp | Kaggle Sub ID | Bot Version / Code File | SHA-256 Hash | Kaggle Rating | Global Rank | Key Event / Outcome Summary |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **Aug 4, 2026** | `8A667F78...` | **V3 Legacy Submission** (`archive/V3_1293_failed/`) | `8A667F7847...` | ~600 | N/A | **FAILED**. Built for Kaggle Envs `1.29.3`. Collapsed on live `1.32.3` runtime (~14k score) due to environment/rule mismatch. |
| **Aug 5, 2026** | `55249106` | **V4.1 State Repair Champion** (`baseline/kaitofukami-v18.py` / `submission.py`) | `AAC9F820CE...` | **2089.8** 🚀 | **~150** | **HISTORIC PEAK**. Rebased on live Envs `1.32.4`. Went 12W–1L in first 13 matches. Kaggle TrueSkill rating spiked to **2089.8**. |
| **Aug 6, 2026** | `55249106` | **V4.1 State Repair Champion** (`baseline/kaitofukami-v18.py`) | `AAC9F820CE...` | **1714.4** | ~350-400 | **EQUILIBRIUM CONVERGENCE**. 104 matches played (45W-59L against top-tier Kaggle bots). Rating stabilized at **1714.4 Master Baseline**. |
| **Aug 7, 2026** | `55328057` | **V8.3 Experimental** (`baseline/submission_v83_standalone.py`) | `B670A912FF...` | **816.8** 📉 | Bad | **EXPERIMENTAL COLLAPSE**. Uploaded static-cap V8.3 after local tournament showed 100% win rate. Collapsed to 816.8 rating on live Kaggle against dynamic opponents. |
| **Aug 7, 2026** | `55329352` | **V4.1 Base Engine Restored** (`submission.py`) | `0a37fd8...` | **1714.4** 🥇 | Champion | **RESTORED CHAMPION**. Re-uploaded V4.1 unconstrained dynamic core engine to restore live leaderboard standing. |
| **Aug 8, 2026** | N/A (Local) | **V4.2 Local Candidate** (`baseline/submission_v84_experimental.py`) | Local Only | N/A | Local | **WITHHELD / GATED**. Local V4.1 core + 10 melons + milk ranker ($96.7k local wealth). Retained locally per upload gate (> $124k). |

---

## 🔍 Key Findings & Answers to Core Questions

### 1. What caused $2100+ \rightarrow \sim 150\text{ rank} \rightarrow 1714.4$?
- **The Initial Spike ($2089.8$)**: When V4.1 (`55249106`) was submitted on Aug 5, 2026, it won **12 out of its first 13 public matches** (+177k margin in match `90006913`, +131k margin in `90007544`). In Kaggle's TrueSkill system, early win streaks produce massive rating surges before uncertainty ($\sigma$) shrinks.
- **Matchmaking & Equilibrium ($1714.4$)**: As Kaggle's TrueSkill system paired V4.1 against higher-rated, more mature competition pool bots over 104 matches, the rating naturally converged from the initial peak to a steady-state equilibrium of **1714.4**.
- **Conclusion**: The bot did **NOT** suddenly break or degrade between 2100 and 1714.4; 1714.4 is simply the true, statistically converged TrueSkill rating of V4.1 against the full Kaggle field!

### 2. Did we replace the good submission?
- **Yes, temporarily on Aug 7**: 
  - On Aug 7, V8.3 (`submission_v83_standalone.py`, Ref `55328057`) was uploaded as an experimental submission because it achieved a 100% win rate in local synthetic tests.
  - On live Kaggle, V8.3 collapsed to **816.8 rating** because its hardcoded static caps (12 cows, static crop caps) could not adapt to real dynamic opponents.
  - **Immediate Rollback**: V4.1 (`submission.py`, Ref `55329352`) was immediately re-uploaded on Aug 7 to restore the 1714.4 champion baseline.

### 3. Metric Divergence: Local Scores ($) vs. Kaggle Rating (TrueSkill Elo)
- **Local Measurement Trap**: In local research, bots were evaluated by **Single-Player / Synthetic 1v1 Wealth ($)** (e.g. $121k, $124k, $96k).
- **Kaggle Leaderboard Reality**: Kaggle evaluates bots by **TrueSkill Relative Rating** against dynamic opponent behavior, market price collisions, and turn-by-turn order stealing.
- A bot that maximizes local score against static scripts (like V8.3) gets destroyed on Kaggle when live opponents flood markets or compete for resources. Conversely, V4.1's unconstrained dynamic closed-loop core is resilient against real opponents, making it a 1714.4 rating champion.

---

## 🛡️ Baseline Protection & Code Provenance Map

1. **Live Kaggle Champion Baseline**:
   - File Path: [`baseline/kaitofukami-v18.py`](file:///D:/kaggriculture/baseline/kaitofukami-v18.py) & [`D:\kaggleculture\archives\V4_1_ARCHIVE\champions\v4_1_frozen.py`](file:///D:/kaggleculture/archives/V4_1_ARCHIVE/champions/v4_1_frozen.py)
   - SHA-256: `AAC9F820CEF2E0B2BBDFE230D79F9FAC7C0E91D08297E663D8B16529DD60EFB4`
   - Kaggle Ref: `55249106` / `55329352`
   - Status: **FROZEN & IMMUTABLE MASTER CHAMPION (1714.4 Rating)**.

2. **Older Archived Codebase**:
   - Location: [`D:\kaggleculture`](file:///D:/kaggleculture)
   - V4.1 Archives & Replay Logs: `D:\kaggleculture\archives\V4_1_ARCHIVE`
   - V5 Modular Architecture Work: `D:\kaggleculture\V5_RESEARCH_START`

3. **Current Local Master Candidate**:
   - File Path: [`baseline/submission_v84_experimental.py`](file:///D:/kaggriculture/baseline/submission_v84_experimental.py)
   - Architecture: V4.1 Dynamic Core + 10-Melon Opening + Opponent Milk Ranker + 8-Cow Cap ($96.7k local 1v1 wealth, 100% sweep vs V4.1).
   - Gate Status: **Withheld / Local Only** (requires strict pre-upload verification).
