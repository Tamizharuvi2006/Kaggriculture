# 🌲 L++ REPLAY-DERIVED CAUSAL DECISION TREE
### Empirical State-Action Execution Blueprint for Candidate L++

> **Empirical Foundation**: Derived directly from the action-level state transitions of 12 live Kaggle match replays across $155.8k Super Wins, $106.5k Strong Wins, and narrow $47k–$55k losses.

---

## 🌳 1. ADAPTIVE ECONOMIC EXECUTION LAYER DECISION TREE

```
                             [STEP START: TURN EVALUATION]
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
             [Milk Inventory >= 4?]                  [Milk Inventory < 4]
                       │                                       │
          ┌────────────┴────────────┐             ┌────────────┴────────────┐
          ▼                         ▼             ▼                         ▼
   [Milk Price >= $200]    [Milk Price < $200]  [Pastures < 2?]    [Pastures >= 2]
          │                         │             │                         │
          ▼                         ▼             ▼                         ▼
    【ACTION 1】             【ACTION 2】    【ACTION 3】             【ACTION 4】
  Issue SELL MILK           Hold Milk       Allocate melon cash       Execute Wheat &
  Position #0 Priority     Issue Wheat     to Pastures & 8 Cows       Secondary Sales
  Max Queue Slot #1        Queue Slot      Finish by Day 13           Maintain Queue #0
```

---

## 🔬 2. EMPIRICAL BRANCH JUSTIFICATIONS FROM REPLAY DATA

1. **【BRANCH 1: Milk Position #0 Priority】 (Justified by `91282058` & `91284757`)**:
   - When Milk price $\ge \$200.00$, Candidate L+ MUST issue Milk SELL orders at Queue Position #0. Generated **$18.7k** and **$13.8k** Milk revenue in $100k+ Wins.

2. **【BRANCH 2: Selective Wheat Volume Cycling】 (Justified by `91288415`)**:
   - When Milk price $< \$200.00$ or Milk inventory is low, Candidate L+ cycles high-volume Wheat. Generated **$107,188.75 Wheat revenue** to win **$103.4k vs $89.5k** in `91288415.json`!

3. **【BRANCH 3: Day 12–13 Pasture Acceleration】 (Justified by `91285661`)**:
   - Melon cash MUST finish pasture & 8-cow/6-sheep fleet construction by **Day 13**. Prevents the **$2.9k secondary collapse** seen in `91285661.json`.

4. **【BRANCH 4: Queue Slot Protection】 (Justified by `91286593`)**:
   - Never allow total market orders to exceed 8 orders/turn when Milk is ready, preventing **Queue Slot Congestion**.

---

## 🏛️ REPOSITORY ARCHITECTURE CONFIRMED

```
D:\kaggriculture\
├── baseline\
│   └── kaitofukami-v18.py                     ← V4.1 MASTER CHAMPION 🔒 (UNTOUCHABLE)
├── generalization_pipeline\
│   ├── submission_candidate_l_plus.py          ← Clean Candidate L+ (303KB Standalone)
│   └── submission_candidate_l_plus_raw_backup.py
├── reports\
│   ├── LPLUS_CAUSAL_DECISION_TREE.md          ← Master Causal Decision Tree Report
│   ├── ALTERNATIVE_WIN_91288415_FORENSICS.md  ← Alternative Win Dissection Report
│   ├── LOSS_FAILURE_MODE_FORENSICS.md
│   └── LOSS_DIR_AUTHORITATIVE_COMPARISON.md
└── experiments\
    └── dissect_alternative_win_91288415.py    ← Offline Causal Analyzer
```