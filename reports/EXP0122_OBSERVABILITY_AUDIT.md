# 🛡️ EXP-0122: OBSERVATION SCHEMA & LEGALITY AUDIT

> **Target Hypothesis**: `EXP-0122` (`OPPONENT_INVENTORY_FRONT_RUNNING`)  
> **Environment**: Pinned `kaggle_environments v1.32.6`  
> **Evaluation**: Verification of public observation schema and information boundary rules.

---

## 🔍 Exact Observation Schema Findings

```
================================================================================
[OFFICIAL KAGGLE OBSERVATION SCHEMA: PLAYER 0 PERSPECTIVE]
================================================================================

  • obs['step']                : int (Step 0..720)                 [PUBLIC]
  • obs['day']                 : int (Day 0..29)                   [PUBLIC]
  • obs['hour']                : int (Hour 0..23)                  [PUBLIC]
  • obs['player']              : int (0 or 1)                      [PUBLIC]
  • obs['private']['shed']     : dict (OWN Milk, Wool, Crops)      [PRIVATE TO PLAYER 0]
  • obs['private']['seeds']    : dict (OWN Unplanted Seeds)        [PRIVATE TO PLAYER 0]

  • obs['farms'][0] (OWN FARM):
      - money                  : float                             [PUBLIC]
      - tiles                  : 10x10 grid (Crop stages, animals) [PUBLIC]
      - farmer                 : [x, y] coordinates               [PUBLIC]
      - hands                  : [[x,y], ...] worker coordinates   [PUBLIC]
      - unlocked_quadrants     : ['NW', 'NE', ...]                 [PUBLIC]

  • obs['farms'][1] (OPPONENT FARM):
      - money                  : float                             [PUBLIC]
      - tiles                  : 10x10 grid (Opponent crops/cows)  [PUBLIC]
      - farmer                 : [x, y] coordinates               [PUBLIC]
      - hands                  : [[x,y], ...] worker coordinates   [PUBLIC]
      - unlocked_quadrants     : ['NW', ...]                       [PUBLIC]
      - ❌ shed / inventory     : NOT PRESENT IN FARMS[1]           [STRICTLY PRIVATE]

  • obs['market']['prices']    : dict (Commodity Spot Prices)      [PUBLIC]
  • obs['market']['inventory'] : dict (Town Market Pool Volume)    [PUBLIC]
================================================================================
```

---

## ⚖️ Formal Verdict: `INVALID_OBSERVABILITY`

1. **Information Barrier**: The opponent's shed inventory is stored in the opponent's private observation dictionary (`obs['private']['shed']`) and is **never transmitted to Player 0**.
2. **Strict Rule Compliance**: Antigravity agents may only utilize information legitimately received via the official `agent(obs)` entry point. Inferring or assuming direct access to `farms[1]['inventory']` is invalid.
3. **Protocol Enforced**: In accordance with research governance, `EXP-0122` is formally marked **`INVALID_OBSERVABILITY`** and closed without compute expenditure.
4. **Transition to EXP-0123**: The Research Council immediately transitions to **`EXP-0123` (`TOWN_SHOP_FEED_PREEMPTION` / `RESOURCE_DENIAL`)**, which relies strictly on **100% verified public observation keys** (`obs['market']['prices']`, `obs['market']['inventory']`, `obs['farms'][1]['money']`, and `obs['town']`).
