# FastSim Engine Reference Manual: Official Kaggriculture Specification

**Source File**: `kaggle_environments/envs/kaggriculture/kaggriculture.py`  
**Standard Configuration**: 720 steps, 30 days, 24 turns/day, 10x10 board, $3,000 starting cash, 100 shed capacity.

---

## 1. Board & Geography

- **Board Dimensions**: $10 \times 10$ tiles (100 tiles total), split into four $5 \times 5$ quadrants:
  - **NW** (x: 0..4, y: 0..4): Unlocked at start ($0 cost).
  - **NE** (x: 5..9, y: 0..4): Unlocked 1st ($1,000 cost).
  - **SW** (x: 0..4, y: 5..9): Unlocked 2nd ($2,000 cost).
  - **SE** (x: 5..9, y: 5..9): Unlocked 3rd ($4,000 cost).
- **Shed Access Tiles**: 4 central inner corners: `[(4,4), (5,4), (4,5), (5,5)]` (NWSE order).
- **Farmer Spawn**: Default spawn is `(4,4)` (first free shed-access tile in NW quadrant).
- **Movement**: `NORTH (0, -1)`, `SOUTH (0, 1)`, `EAST (1, 0)`, `WEST (-1, 0)`. Moving onto `LOCKED` tiles is allowed, but tile actions no-op on locked tiles.

---

## 2. Crop Taxonomy & Growth Dynamics

| Crop | Seed Cost | First Yield Day | Max Yield Day | Interval | Max Yield | Ongoing? | Yield Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WHEAT** | $10 | Day 2 | Day 4 | 0 | 6 units | No | Single harvest; +1/day watered during window (Days 2–4). Clears tile. |
| **CARROT** | $20 | Day 2 | Day 3 | 0 | 4 units | No | Single harvest; +1/day watered during window (Days 2–3). Clears tile. |
| **TOMATO** | $50 | Day 8 | Day 8 | 1 day | 4 units | Yes | Regrows every 1 day after Day 8 if watered. |
| **STRAWBERRY** | $100 | Day 10 | Day 10 | 2 days | 4 units | Yes | Regrows every 2 days after Day 10 if watered (+2 if fertilized). |
| **MELON** | $80 | Day 10 | Day 12 | 0 | 6 units | No | Single harvest; +1/day watered during window (Days 6–12). Clears tile. |

- **Watering & Death**: If a crop is unwatered for 2 consecutive days, it dies and turns into `WEED`.
- **Plant Lifespan & Decay**: Non-ongoing ripe crops begin decaying at `max_lifespan_step = (planted_day + max_yield_day + 1) * 24`. Every 2 steps past MLS, yield drops by 1. At 0, becomes `WEED`.

---

## 3. Livestock Taxonomy & Care

| Animal | Purchase Cost | Structure | First Yield Day | Interval | Max Held | Product |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GOOSE** | $300 | COOP | Day 4 | 1 day | 4 units | **EGG** |
| **COW** | $400 | PASTURE | Day 8 | 2 days | 6 units | **MILK** |
| **SHEEP** | $500 | PASTURE | Day 6 | 3 days | 6 units | **WOOL** |

- **Feeding (`FEED`)**: Consumes 1 **WHEAT** from inventory. If unfed for 2 consecutive days, animal escapes!
- **Manure (`COLLECT_FERTILIZER`)**: Mature animals generate 1 `FERTILIZER` daily.
- **Care (`CARE`)**: If fed and cared for today, yields +1 bonus unit on next production day.

---

## 4. Market Pricing & Simultaneous Lockstep Resolution

### Pricing Formula:
$$\text{price}(I) = \text{base} + \text{sign} \times \text{amp} \times f(|I - I_0|)$$
* $I_0 = 10,000$, $\text{Price Floor} = \$1$.
* $\text{amp} = \frac{\text{target} \times \text{base}}{f(T)}$.

| Product | Base Price | Target Capacity ($T$) | Below Function ($I < I_0$) | Below Target | Above Function ($I > I_0$) | Above Target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WHEAT** | $25 | 400 | `sqrt` | 0.80 | `log` | 0.20 |
| **CARROT** | $35 | 450 | `hinge` | 1.00 | `sqrt` | 0.70 |
| **TOMATO** | $60 | 200 | `hinge` | 0.40 | `sqrt` | 0.60 |
| **STRAWBERRY** | $120 | 100 | `sqrt` | 0.70 | `linear` | 1.60 |
| **MELON** | $250 | 300 | `log` | 0.20 | `sq` | 3.60 |
| **EGG** | $50 | 332 | `hinge` | 0.40 | `log` | 0.20 |
| **MILK** | $160 | 122 | `sqrt` | 0.60 | `linear` | 1.60 |
| **WOOL** | $200 | 105 | `log` | 0.20 | `sq` | 3.20 |
| **FERTILIZER** | $100 | 200 | `linear` | 0.40 | `linear` | 0.40 |

### Per-Unit Lockstep Resolution:
1. Atomic orders (`HIRE`, `BUY_LAND`) execute first in player order ($P0 \rightarrow P1$).
2. Per-unit loop: Quote both players' current units at pre-commit inventory simultaneously.
3. Commit both units. If successful, decrement remaining order count.
4. Refresh prices after every order index in queue.

---

## 5. Town Consumption & End-of-Day Mechanics

- **Town Shops Consumption**: Every 4 turns (`step % 4 == 0`), unlocked town shops consume 1 of each product (2x for single-product shops like Yarn Store, Pet Cafe).
- **Town Center Consumption**: Every 24 turns (`step % 24 == 0`), consumes 1 of every non-fertilizer product.
- **End-of-Day (Every 24 turns)**:
  - Stable RNG: `random.Random((seed * 1_000_003) ^ day)`.
  - Refresh plants & animals.
  - Spawn weeds with probability 0.005 on empty tiles.
  - Drop all farmer/hand inventories into shed (capacity 100).
  - Reset farmer to `(4,4)`, despawn all hands, reset `hires_today = 0`.
  - Every 3 days (Day 3, 6, 9...): Unlock 1 random shop from `SHOPS` (max 8 instances).

---

## 6. Terminal Reward
At Step 718/719, game sets `status = DONE` and `reward = float(money)`.
