# 📊 APEX 3.5 Live Match Tracker & Loss Forensics

> **Candidate Reference**: `Ref 55483322` (`submission_candidate_apex35.py`)
> **Current Visible Kaggle Rating**: **1088.0**
> **Total Ingested Live Matches**: **56 matches (26W - 30L - 0T | 46.4% Win Rate)**
> **Mean Wealth**: **$81,953.41** vs Opponent **$77,147.46** (Net Margin: **$+4,805.95**)

---

## 📈 1. Tier-by-Tier Ladder Breakdown

| Opponent Elo Tier | Matches | Record (W-L) | Win Rate (%) | Our Mean Wealth ($) | Mean Margin ($) | Competitive Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tier A (< 1100 Elo)** | 22 | 15W - 7L | **68.2%** | $83,814.18 | **$+14,041.68** | Saturated exploitation & strong positive margin |
| **Tier B (1100-1200 Elo)** | 26 | 9W - 17L | **34.6%** | $81,840.23 | **$-729.08** | Primary ladder battleground |
| **Tier C (1200-1300 Elo)** | 8 | 2W - 6L | **25.0%** | $77,204.12 | **$-2,603.50** | Strong competitive tier |
| **Tier D (1300+ Elo)** | 0 | 0W - 0L | **0.0%** | $0.00 | **$+0.00** | Elite ceiling tier |

---

## 🔍 2. Complete Live Loss Forensics Log (30 Matches)

| Episode ID | Date/Time (UTC) | Opponent Sub ID | Opponent Initial Elo | Our Wealth ($) | Opp Wealth ($) | Margin ($) | Loss Classification | Forensic Analysis |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| [92654227](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92654227) | 2026-08-13 12:59 | 55471702 | 952.0 | $108,473.0 | $109,623.0 | **$-1,150.0** | Symmetric Nash Parity | Tight high-volume mirror split (> $95k both, < 3% margin). |
| [92657061](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92657061) | 2026-08-13 13:11 | 55483232 | 1098.0 | $83,211.0 | $100,011.0 | **$-16,800.0** | Hoarding Rebound Variance | Harsh mid-game crash; opponent inventory rescued by late spike. |
| [92659893](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92659893) | 2026-08-13 13:23 | 55482179 | 1166.6 | $93,228.0 | $93,816.0 | **$-588.0** | Standard Competitive Loss | Competitive divergence during mid/late-game clearance. |
| [92662754](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92662754) | 2026-08-13 13:35 | 55476677 | 1286.0 | $124,237.0 | $127,177.0 | **$-2,940.0** | Symmetric Nash Parity | Tight high-volume mirror split (> $95k both, < 3% margin). |
| [92662787](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92662787) | 2026-08-13 13:35 | 55482597 | 1154.5 | $109,693.0 | $112,074.0 | **$-2,381.0** | Symmetric Nash Parity | Tight high-volume mirror split (> $95k both, < 3% margin). |
| [92663703](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92663703) | 2026-08-13 13:39 | 55275139 | 1202.9 | $60,274.0 | $61,554.0 | **$-1,280.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92665598](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92665598) | 2026-08-13 13:47 | 55247701 | 1176.1 | $124,344.0 | $125,630.0 | **$-1,286.0** | Symmetric Nash Parity | Tight high-volume mirror split (> $95k both, < 3% margin). |
| [92670343](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92670343) | 2026-08-13 14:07 | 55266412 | 1165.8 | $37,513.0 | $39,076.0 | **$-1,563.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92672213](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92672213) | 2026-08-13 14:15 | 55436474 | 1181.4 | $42,298.0 | $50,345.0 | **$-8,047.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92673149](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92673149) | 2026-08-13 14:19 | 55293479 | 1198.3 | $65,864.0 | $72,159.0 | **$-6,295.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92676926](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92676926) | 2026-08-13 14:35 | 55286551 | 1164.8 | $93,267.0 | $95,494.0 | **$-2,227.0** | Standard Competitive Loss | Competitive divergence during mid/late-game clearance. |
| [92677877](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92677877) | 2026-08-13 14:39 | 55257118 | 1164.1 | $65,382.0 | $67,446.0 | **$-2,064.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92678835](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92678835) | 2026-08-13 14:44 | 55430675 | 1211.7 | $85,802.0 | $89,300.0 | **$-3,498.0** | Standard Competitive Loss | Competitive divergence during mid/late-game clearance. |
| [92680700](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92680700) | 2026-08-13 14:51 | 55484024 | 1132.8 | $84,752.0 | $87,246.0 | **$-2,494.0** | Standard Competitive Loss | Competitive divergence during mid/late-game clearance. |
| [92682596](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92682596) | 2026-08-13 14:59 | 55449124 | 1180.6 | $63,447.0 | $64,890.0 | **$-1,443.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92684467](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92684467) | 2026-08-13 15:07 | 55473510 | 1134.4 | $95,885.0 | $99,163.0 | **$-3,278.0** | Standard Competitive Loss | Competitive divergence during mid/late-game clearance. |
| [92685417](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92685417) | 2026-08-13 15:11 | 55424868 | 1153.7 | $58,580.0 | $59,640.0 | **$-1,060.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92697574](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92697574) | 2026-08-13 16:03 | 55486730 | 1238.1 | $30,536.0 | $37,912.0 | **$-7,376.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92710604](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92710604) | 2026-08-13 17:00 | 55449124 | 1181.9 | $82,266.0 | $82,685.0 | **$-419.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92721694](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92721694) | 2026-08-13 17:48 | 55479991 | 1063.9 | $29,835.0 | $31,604.0 | **$-1,769.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92744887](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92744887) | 2026-08-13 19:35 | 55427130 | 1133.8 | $61,604.0 | $62,556.0 | **$-952.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92745505](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92745505) | 2026-08-13 19:39 | 55489697 | 1106.3 | $87,342.0 | $101,420.0 | **$-14,078.0** | Hoarding Rebound Variance | Harsh mid-game crash; opponent inventory rescued by late spike. |
| [92753772](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92753772) | 2026-08-13 20:15 | 55490433 | 1055.8 | $37,023.0 | $50,334.0 | **$-13,311.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92760409](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92760409) | 2026-08-13 20:43 | 55489796 | 1284.6 | $53,075.0 | $62,355.0 | **$-9,280.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92781573](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92781573) | 2026-08-13 22:16 | 55491492 | 1046.3 | $40,581.0 | $44,116.0 | **$-3,535.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92782407](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92782407) | 2026-08-13 22:20 | 55491894 | 1049.6 | $58,995.0 | $83,824.0 | **$-24,829.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92792740](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92792740) | 2026-08-13 23:04 | 55490888 | 1171.1 | $78,190.0 | $81,542.0 | **$-3,352.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92820867](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92820867) | 2026-08-14 01:08 | 55437267 | 1210.8 | $64,106.0 | $64,705.0 | **$-599.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92821576](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92821576) | 2026-08-14 01:12 | 55493956 | 1041.8 | $65,772.0 | $66,490.0 | **$-718.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |
| [92873490](https://www.kaggle.com/competitions/kaggriculture/leaderboard?dialog=episodes-episode-92873490) | 2026-08-14 04:56 | 55497749 | 1149.6 | $61,892.0 | $67,021.0 | **$-5,129.0** | Harsh Commodity Crash | Depressed price trajectory across entire match; both agents low. |

---

## 📜 3. Standing Live Monitoring Orders

1. **APEX 3.5 Code is 100% FROZEN**: No code edits, no re-tuning, no new submission uploads.
2. **Telemetry Collection Only**: Continuously ingest completed matches and track rating as it progresses through the 1100, 1200, and 1300+ Elo brackets.
3. **Repeated Failure Threshold**: If a systematic new failure mode appears across multiple matches in the same cohort, report the evidence before considering any research hypotheses.
