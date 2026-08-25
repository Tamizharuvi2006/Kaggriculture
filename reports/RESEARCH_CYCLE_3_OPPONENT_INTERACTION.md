# 🧠 RESEARCH CYCLE #3: OPPONENT INTERACTION & PUBLIC-STATE REFLEXIVITY REPORT

> **Objective**: Formulate and rank genuinely fresh, game-theoretic opponent-relative mechanisms using **strictly 100% legal, public observation state**.  
> **Source Base**: 807 Tournament Matches, 86 Trajectories, and Completed `EXP-0113`–`EXP-0124` Ledger.

---

## 🏛️ 1. Permanent Closure of the Land Expansion Family

With the completion of the two-step causal disentanglement (`EXP-0121` and `EXP-0124`), the **`LAND_EXPANSION_PACING`** family is permanently closed:
* **`EXP-0121` (Insolvent Early Purchase @ $1,100)**: ❌ **4.3% WR (-$4,069 MCV)** $ightarrow$ Ruinous capital starvation.
* **`EXP-0124` (Solvent Early Purchase @ $1,800)**: 🟡 **50.0% WR (-$94 MCV)** $ightarrow$ 100% solvent, but exactly neutral edge.
* **Causal Law**: Early land expansion is a *consequence* of accumulated wealth, not a *cause* of victory.

---

## 📊 2. Top-5 Ranked Opponent-Relative Research Queue

| Rank | Hypothesis ID | Target Strategy | Public Observable Key | Real Frequency | Causal Confidence | Priority Score | Status |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **#1** | **`EXP-0125`** | **`OPPONENT_PUBLIC_FIELD_RIPE_CROP_FRONT_RUNNING`** | `obs['farms'][1]['tiles'] (Public...` | 72.4% of tournament matches | **0.89** | **`1.95`** | `RECOMMENDED_PRIMARY` |
| **#2** | **`EXP-0126`** | **`OPPONENT_COW_CYCLE_MILK_LIQUIDATION_TIMING`** | `obs['farms'][1]['tiles'] (Public...` | 88.1% of tournament matches | **0.82** | **`1.54`** | `BACKLOG_RANK_2` |
| **#5** | **`EXP-0129`** | **`DYNAMIC_SLIPPAGE_AWARE_BATCHING`** | `obs['market']['prices'] & obs['m...` | 100% of matches | **0.75** | **`1.22`** | `BACKLOG_RANK_4` |
| **#3** | **`EXP-0127`** | **`OPPONENT_CASH_STARVATION_AUCTION_PRESSURE`** | `obs['farms'][1]['money'] (Public...` | 18.5% of tournament matches | **0.65** | **`0.92`** | `BACKLOG_RANK_3` |
| **#4** | **`EXP-0128`** | **`REFLEXIVE_QUADRANT_CONGESTION_AVOIDANCE`** | `obs['farms'][1]['unlocked_quadra...` | 100% of matches | **0.20** | **`0.25`** | `LOW_PRIORITY` |

---

## 🏆 3. Recommended Primary Direction: `EXP-0125` (`OPPONENT_PUBLIC_FIELD_RIPE_CROP_FRONT_RUNNING`)

### 🔍 A. Observability Legality Audit (PASS ✅)
* **Exact Path**: `obs['farms'][1]['tiles']`
* **Legality**: The opponent's 10x10 farmland grid is **100% public** at every timestep $t$.
* **Visible Attributes**: Tile coordinates, crop type (`STRAWBERRY`), and growth stage (`stage == 'RIPE'`).

### 🔬 B. Mechanism Feasibility Audit (PASS ✅)
* **The Game-Theoretic Signal**: Strawberry crops take 48 steps to mature. When $\ge 4$ tiles on the opponent's field turn ripe at Step $t$, the opponent's farmer/workers will harvest and liquidate those strawberries within 1–2 steps.
* **The Reflexive Action**: When APEX detects $\ge 4$ ripe strawberries on the opponent's field, if APEX holds $\ge 2$ strawberries in its shed, APEX executes **immediate liquidation on Step $t$**.
* **The Competitive Payoff**: APEX captures peak market price ($P \approx \$135\text{--}\$150/\text{unit}$) and forces the opponent's subsequent dump to absorb the resulting market slippage.
