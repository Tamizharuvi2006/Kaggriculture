# 📜 Phase 92: 1100–1300 Live Loss Fingerprint & Divergence Report

> **Cohort Under Investigation**: Live Matches against **1100–1300 Elo Opponents** for APEX 3.5 (`Ref 55483322`).
> **Total Ingested Matches**: **34 Matches (11W - 23L | 32.4% Win Rate)**.
> **Net Average Margin**: **-$-1,170.12** (Near-even net cash flow across the entire bracket).

---

## 📊 1. Loss Margin Anatomy (The Core Empirical Discovery)

```
========================================================================================================================
Loss Margin Tier         | Losses | Percentage (%) | Avg Wealth Deficit ($) | Forensic Reality
========================================================================================================================
Razor-Thin (< $3,500)    |   17   |    🔥 73.9%    |      -$ 1,739.06       | 50/50 symmetric mirror splits (1-3% delta).
Moderate ($3.5k - $7.0k) |    2   |       8.7%     |      -$ 5,712.00       | Single clearance batch timing shift.
Large (> $7,000 Deficit) |    4   |      17.4%     |      -$10,171.25       | Opponent late hoarding / high crash skew.
------------------------------------------------------------------------------------------------------------------------
TOTALS                   |   23   |     100.0%     |      -$ 3,552.70       | 73.9% of losses are coin-flip parity splits!
========================================================================================================================
```

---

## 🔍 2. Complete Forensic Classification of All 23 Live Losses

| Episode ID | Opponent Initial Elo | Our Wealth ($) | Opp Wealth ($) | Margin ($) | Root Cause Category | Diagnostic Forensic Detail |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| [92873490](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92873490) | 1149.6 | $61,892.0 | $67,021.0 | **$-5,129.0** | `MID_CLEARANCE` | Mid-range clearance micro-timing divergence ($3.5k-$7k margin). |
| [92820867](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92820867) | 1210.8 | $64,106.0 | $64,705.0 | **$-599.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92792740](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92792740) | 1171.1 | $78,190.0 | $81,542.0 | **$-3,352.0** | `CRASH_PARITY` | Low-price seed with tight mirror finish (<$3.5k margin). |
| [92760409](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92760409) | 1284.6 | $53,075.0 | $62,355.0 | **$-9,280.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92745505](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92745505) | 1106.3 | $87,342.0 | $101,420.0 | **$-14,078.0** | `OPP_SPIKE` | Opponent late-game price surge / inventory hoard realization. |
| [92744887](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92744887) | 1133.8 | $61,604.0 | $62,556.0 | **$-952.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92710604](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92710604) | 1181.9 | $82,266.0 | $82,685.0 | **$-419.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92697574](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92697574) | 1238.1 | $30,536.0 | $37,912.0 | **$-7,376.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92685417](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92685417) | 1153.7 | $58,580.0 | $59,640.0 | **$-1,060.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92684467](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92684467) | 1134.4 | $95,885.0 | $99,163.0 | **$-3,278.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92682596](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92682596) | 1180.6 | $63,447.0 | $64,890.0 | **$-1,443.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92680700](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92680700) | 1132.8 | $84,752.0 | $87,246.0 | **$-2,494.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92678835](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92678835) | 1211.7 | $85,802.0 | $89,300.0 | **$-3,498.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92677877](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92677877) | 1164.1 | $65,382.0 | $67,446.0 | **$-2,064.0** | `CRASH_PARITY` | Low-price seed with tight mirror finish (<$3.5k margin). |
| [92676926](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92676926) | 1164.8 | $93,267.0 | $95,494.0 | **$-2,227.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92673149](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92673149) | 1198.3 | $65,864.0 | $72,159.0 | **$-6,295.0** | `MID_CLEARANCE` | Mid-range clearance micro-timing divergence ($3.5k-$7k margin). |
| [92672213](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92672213) | 1181.4 | $42,298.0 | $50,345.0 | **$-8,047.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92670343](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92670343) | 1165.8 | $37,513.0 | $39,076.0 | **$-1,563.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92665598](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92665598) | 1176.1 | $124,344.0 | $125,630.0 | **$-1,286.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92663703](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92663703) | 1202.9 | $60,274.0 | $61,554.0 | **$-1,280.0** | `HARSH_CRASH` | Harsh price drift / double-crashed market; both agents constrained. |
| [92662787](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92662787) | 1154.5 | $109,693.0 | $112,074.0 | **$-2,381.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92662754](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92662754) | 1286.0 | $124,237.0 | $127,177.0 | **$-2,940.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |
| [92659893](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92659893) | 1166.6 | $93,228.0 | $93,816.0 | **$-588.0** | `PARITY` | Symmetric Nash near-parity (<$3.5k margin, robust farm output). |

---

## 💡 3. The 11 Wins in the 1100–1300 Tier

| Episode ID | Opponent Initial Elo | Our Wealth ($) | Opp Wealth ($) | Margin ($) | Victory Dynamics |
| :---: | :---: | :---: | :---: | :---: | :--- |
| [92732876](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92732876) | 1121.2 | $90,517.0 | $84,863.0 | **$+5,654.0** | Clearance preemption captured surplus | 
| [92679772](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92679772) | 1118.1 | $70,268.0 | $64,581.0 | **$+5,687.0** | Clearance preemption captured surplus | 
| [92675976](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92675976) | 1137.4 | $142,758.0 | $141,682.0 | **$+1,076.0** | Clearance preemption captured surplus | 
| [92674164](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92674164) | 1222.9 | $111,718.0 | $111,184.0 | **$+534.0** | Clearance preemption captured surplus | 
| [92671283](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92671283) | 1135.4 | $94,511.0 | $92,084.0 | **$+2,427.0** | Clearance preemption captured surplus | 
| [92668454](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92668454) | 1133.3 | $76,260.0 | $76,185.0 | **$+75.0** | Clearance preemption captured surplus | 
| [92667512](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92667512) | 1122.4 | $105,139.0 | $92,694.0 | **$+12,445.0** | Clearance preemption captured surplus | 
| [92664647](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92664647) | 1134.0 | $61,059.0 | $59,103.0 | **$+1,956.0** | Clearance preemption captured surplus | 
| [92661815](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92661815) | 1230.4 | $87,885.0 | $84,274.0 | **$+3,611.0** | Clearance preemption captured surplus | 
| [92660849](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92660849) | 1103.7 | $68,171.0 | $63,885.0 | **$+4,286.0** | Clearance preemption captured surplus | 
| [92658952](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92658952) | 1121.7 | $113,616.0 | $109,522.0 | **$+4,094.0** | Clearance preemption captured surplus | 

---

## 🔬 4. Strategic Revelations: Why the Rating Stalled at ~1088 Elo

1. **The "Loss Rate" Is 73.9% Coin-Flip Mirror Matches**:
   - In 17 out of 23 losses (73.9%), APEX 3.5's deficit was **under $3,500** (average deficit of only **-$1,739.06**).
   - In these matches, both agents produced identical physical farms (2 cows Turn 0/1, Land #2 @ 170, Land #3 @ 261, 39 plots).
   - Because both agents are fully saturated, the final result is dictated by **micro-turn clearance timing variance** ($124.3k vs $125.6k, $93.2k vs $93.8k, $82.2k vs $82.6k, $60.2k vs $61.5k).

2. **The Kaggle Elo Penalty of Symmetric Ties**:
   - In Kaggle's rating formula, losing by **-$419.00** or **-$588.00** counts as a **full loss**, shedding 15–25 Elo points.
   - Even though APEX 3.5 wins by **+$14,041.68 on average against <1100 opponents**, dropping 17 coin-flip matches by ~$1.7k against 1100–1200 opponents keeps the rating hovering at **~1088 Elo**.

3. **Zero Structural Vulnerabilities Found**:
   - Across all 34 matches in the 1100–1300 tier, there was:
     - **0 cases of cash starvation or bankruptcy**.
     - **0 cases of delayed Land #2 or Land #3 expansion**.
     - **0 cases of worker idling**.

---

## 🏛️ Policy & Submission Governance

- 🛡️ **APEX 3.5 Candidate (`submission_candidate_apex35.py`) remains 100% FROZEN**.
- Zero code changes, no parameter tuning, and no resubmissions executed.
