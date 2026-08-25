# 🧠 APEX 4.1 HYBRID ML — Complete Implementation Specification

> **For**: Any agent (human or AI) building the ML upgrade for Kaggriculture APEX  
> **Prerequisite reads**: `README.md` (game format, agent architecture), `BASELINE_CONTRACT.md` (release gates)  
> **Date**: August 18, 2026  
> **Status**: PLAN — not yet implemented

---

## Table of Contents

1. [Why Hybrid, Not Pure ML](#1-why-hybrid-not-pure-ml)
2. [Architecture Overview](#2-architecture-overview)
3. [The Existing Agent (What You're Building On)](#3-the-existing-agent-what-youre-building-on)
4. [Upgrade 1: Game Environment Wrapper](#4-upgrade-1-game-environment-wrapper)
5. [Upgrade 2: State Feature Extractor (128-dim)](#5-upgrade-2-state-feature-extractor-128-dim)
6. [Upgrade 3: Opponent Classifier (Layer 3)](#6-upgrade-3-opponent-classifier-layer-3)
7. [Upgrade 4: Strategy Selector — PPO (Layer 2)](#7-upgrade-4-strategy-selector--ppo-layer-2)
8. [Upgrade 5: Market Timing Optimizer (Layer 1)](#8-upgrade-5-market-timing-optimizer-layer-1)
9. [Training Pipeline — Step by Step](#9-training-pipeline--step-by-step)
10. [Integration Into submission.py](#10-integration-into-submissionpy)
11. [Packaging for Kaggle](#11-packaging-for-kaggle)
12. [Validation & Release Gates](#12-validation--release-gates)
13. [File Layout](#13-file-layout)
14. [Hardware & Dependencies](#14-hardware--dependencies)
15. [What NOT to Do](#15-what-not-to-do)
16. [Timeline](#16-timeline)

---

## 1. Why Hybrid, Not Pure ML

The existing APEX 4.0 agent is 4,635 lines of validated Python that handles:
- Full worker pathfinding and crop lifecycle management
- Embedded replay-derived opening schedules (base85-encoded action sequences)
- Dynamic cash buffers, liquidity rescue, end-of-game liquidation
- 4 validated adaptive rules (RULE_01 through RULE_04)
- Exception safety (try/except → `{"farmer": ["PASS"], "hands": [], "market": []}`)

**Pure RL cannot learn all of this** in any reasonable timeframe. The action space is:
- 14 farmer actions × variable hand items × up to 10 market orders per step
- 720 steps per game, 2-player simultaneous
- Sparse reward (only final MCV matters for win/loss)

**Hybrid approach**: Keep APEX 4.0 for execution. Add ML at 3 specific decision points where heuristics are weakest.

| Pure ML | Hybrid ML |
|:---|:---|
| Must learn entire game from scratch | Learns only what matters |
| Millions of games needed | ~10,000 games sufficient |
| Replaces working code | Augments working code |
| High risk of regression | Low risk (fallback to APEX 4.0) |
| Huge model (100K+ params) | Tiny model (~18K params) |

---

## 2. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     APEX 4.1 HYBRID AGENT                       │
│                                                                  │
│  LAYER 3: OPPONENT CLASSIFIER  ──────────────────────────────┐  │
│  Input: 24 opponent features (from obs["farms"][1])           │  │
│  Output: archetype probabilities [5 classes]                  │  │
│  Architecture: MLP(24 → 64 → 32 → 5), softmax               │  │
│  Params: ~2,800                                               │  │
│  Training: Supervised cross-entropy on replay labels           │  │
│  ──────────────────────────────────────────────────────────────│  │
│                        │ archetype_probs                       │  │
│                        ▼                                       │  │
│  LAYER 2: STRATEGY SELECTOR  ────────────────────────────────┐  │
│  Input: 128 game features + 5 archetype probs = 133 dims     │  │
│  Output: strategy weights [4 profiles] + confidence scalar    │  │
│  Architecture: MLP(133 → 64 → 32 → 5), softmax on [0:4]     │  │
│  Params: ~10,400                                              │  │
│  Training: PPO self-play in kaggle_environments               │  │
│  Safety: If confidence < 0.60 → skip, use APEX 4.0 defaults  │  │
│  ──────────────────────────────────────────────────────────────│  │
│                        │ strategy_weights                      │  │
│                        ▼                                       │  │
│  LAYER 1: MARKET TIMING  ────────────────────────────────────┐  │
│  Input: 20-step price window (8 dims × 20 steps = 160)       │  │
│  Output: per-product sell/hold/partial signal [4 products]    │  │
│  Architecture: LSTM(8, hidden=32) → Linear(32 → 3×4)         │  │
│  Params: ~5,300                                               │  │
│  Training: Reward-shaped PPO on MCV delta                     │  │
│  Safety: Only modifies SELL orders, never farmer/hands        │  │
│  ──────────────────────────────────────────────────────────────│  │
│                        │ market_signals                        │  │
│                        ▼                                       │  │
│  LAYER 0: APEX 4.0 EXECUTION ENGINE  ────────────────────────│  │
│  File: APEX4_SUBMISSION_FINAL.py (4,635 lines)               │  │
│  Entry: def agent(obs, configuration=None)                    │  │
│  Contains: full worker pathfinding, crop cycles, schedules,  │  │
│            4 adaptive rules, liquidity rescue, exception safe │  │
│  ML integration point: agent() line 4507 (market_orders)     │  │
│  ──────────────────────────────────────────────────────────────│  │
│                                                                  │
│  TOTAL PARAMS: ~18,500 (~74 KB as float32, ~20 KB compressed)  │
│  INFERENCE TIME: < 5ms per step on CPU                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. The Existing Agent (What You're Building On)

### Key files:
- **Live agent**: [`submission.py`](file:///D:/Kaggriculture/submission.py) — APEX 3.5 (4,572 lines)
- **Sealed candidate**: [`APEX4_SUBMISSION_FINAL.py`](file:///D:/Kaggriculture/APEX4_SUBMISSION_FINAL.py) — APEX 4.0 (4,635 lines)

### How the agent works (simplified):

```python
# submission.py structure:

# Lines 1-204: Constants (CROPS, ANIMALS, DEFAULT_STRATEGY, ANIMAL_SITES)
# Lines 205-226: Global state variables (_OPPONENT_STYLE, _V18_SELECTED_MARKET, etc.)
# Lines 227-440: Embedded base85-encoded opening schedules
# Lines 441-4381: Core game logic (crop cycles, worker routing, market orders, etc.)
# Lines 4382-4462: _base_agent(obs) — the main decision function
# Lines 4464-4572: agent(obs, configuration) — entry point with APEX 3.5 overlays

# The entry point:
def agent(obs, configuration=None):
    step = obs["step"]
    farms = obs["farms"]           # [our_farm, opponent_farm]
    farm0 = farms[0]               # our farm
    money = farm0["money"]
    priv = obs["private"]          # our private state (shed contents)
    shed = priv["shed"]
    mkt = obs["market"]            # market prices
    unlocked = farm0["unlocked_quadrants"]  # ["NW"], ["NW","NE"], etc.
    
    # Step 71 liquidity rescue
    # End-of-game clearance (step >= 700)
    # Dynamic safe cash buffer
    # Price velocity tracking
    # Dual-regime sell logic (cash-constrained vs cash-flushed)
    # 3-quadrant ceiling
    
    act = _base_agent(obs)         # get base action from schedule+heuristics
    # ... apply overlays to act["market"] ...
    return act                     # {"farmer": [...], "hands": [...], "market": [...]}
```

### Observation dict structure (from Kaggle):

```python
obs = {
    "step": 0,                    # 0-719 (720 total steps = 30 days × 24 hours)
    "farms": [
        {   # farms[0] = OUR farm (public info)
            "money": 1000.0,
            "unlocked_quadrants": ["NW"],
            "tiles": [...],       # grid of tile states (crop, stage, water)
            "animals": {"COW": 0, "SHEEP": 0},
            "workers": [          # list of worker positions and states
                {"position": [4, 2], "carrying": None, "carrying_qty": 0},
                ...
            ],
        },
        {   # farms[1] = OPPONENT farm (public info — same structure)
            "money": 1000.0,
            "unlocked_quadrants": ["NW"],
            "tiles": [...],
            "animals": {"COW": 0, "SHEEP": 0},
            "workers": [...],
        },
    ],
    "private": {                  # OUR private info (opponent can't see)
        "shed": {                 # inventory in our shed
            "WHEAT": 0, "CARROT": 0, "TOMATO": 0,
            "STRAWBERRY": 0, "MELON": 0,
            "MILK": 0, "WOOL": 0, "EGG": 0,
            "FERTILIZER": 0,
            "WHEAT_SEEDS": 10, "CARROT_SEEDS": 0, ...
        },
        "orders_pending": [],     # market orders not yet executed
    },
    "market": {
        "prices": {               # current market prices
            "WHEAT": 10.0, "CARROT": 20.0, "TOMATO": 50.0,
            "STRAWBERRY": 120.0, "MELON": 80.0,
            "MILK": 193.0, "WOOL": 150.0,
            "FERTILIZER": 100.0,
        },
        "town_demand": {...},     # town shop demand (affects prices)
    },
}
```

### Valid action format:

```python
action = {
    "farmer": ["MOVE_RIGHT"],     # exactly 1 farmer action (string)
    "hands": ["WHEAT_SEEDS"],     # 0 or 1 items (list of strings)
    "market": [                   # 0 to 10 market orders (list of lists)
        ["SELL", "STRAWBERRY", 4],
        ["BUY_SEED", "MELON", 3],
        ["BUY_LAND", "NE"],
        ["BUY_ANIMAL", "COW"],
        ["HIRE"],
    ],
}
```

### Strategy profiles already in the code:

The agent has 4 built-in strategy profiles (lines 174-203 of submission.py):

| Profile | Key Settings | When Used |
|:---|:---|:---|
| `premium` | 8 cows, 6 sheep, 34 strawberries, $250 reserve | Default balanced play |
| `livestock` | 12 cows, 2 sheep, 34 strawberries, $150 reserve | When opponent is livestock-heavy |
| `wheat_rush` | 12 cows, 2 sheep, 34 strawberries, $150 reserve, 1 animal cap | Aggressive early cash flow |
| `cow_expert` / `sheep_expert` | 12 cows OR 12 sheep | Counter-specific animal profiles |

**ML Layer 2 will learn WHICH profile to select** and with what blend weights, replacing the hand-tuned `rotation_evidence_threshold: 0.9` gate.

---

## 4. Upgrade 1: Game Environment Wrapper

### What to build:

```python
# File: D:/Kaggriculture/apex_next/ml_engine/env_wrapper.py

import kaggle_environments
import numpy as np
from feature_extractor import extract_features

class KaggriculureGymEnv:
    """Wraps kaggle_environments for RL training.
    
    This is the CRITICAL piece that was completely missing from the
    old ML pipeline. The old pipeline used np.random.randn() instead
    of this.
    """
    
    def __init__(self, opponent_fn=None):
        """
        Args:
            opponent_fn: callable(obs, config) -> action_dict
                         The opponent agent to train against.
                         If None, uses a copy of APEX 3.5.
        """
        self.env = kaggle_environments.make(
            "kaggriculture",
            configuration={"episodeSteps": 720}
        )
        self.opponent_fn = opponent_fn or self._default_opponent
        self.feature_dim = 128
        self.step_count = 0
        
    def reset(self, seed=None):
        """Reset environment and return initial observation features."""
        self.state = self.env.reset(num_agents=2)
        self.step_count = 0
        obs = self.state[0].observation
        return extract_features(obs)
    
    def step(self, our_action_dict):
        """
        Take one step in the environment.
        
        Args:
            our_action_dict: {"farmer": [...], "hands": [...], "market": [...]}
            
        Returns:
            features: np.array shape (128,) — game state features
            reward: float — our MCV minus opponent MCV
            done: bool — episode finished
            info: dict — raw observation for debugging
        """
        # Get opponent action
        opp_obs = self.state[1].observation
        opp_action = self.opponent_fn(opp_obs, {})
        
        # Step environment with both actions
        self.state = self.env.step([our_action_dict, opp_action])
        self.step_count += 1
        
        obs = self.state[0].observation
        features = extract_features(obs)
        
        done = self.state[0].status == "DONE"
        
        if done:
            our_mcv = self.state[0].reward or 0
            opp_mcv = self.state[1].reward or 0
            reward = our_mcv - opp_mcv  # positive = we won
        else:
            reward = 0.0  # sparse reward — only at end of episode
        
        info = {"obs": obs, "step": self.step_count}
        return features, reward, done, info
    
    def _default_opponent(self, obs, config):
        """Fallback: import APEX 3.5 as opponent."""
        # Import the live agent function
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apex35", "D:/Kaggriculture/submission.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent(obs, config)
```

### Speed benchmark:
- `kaggle_environments` runs at ~35 games/sec on CPU
- Each game = 720 steps
- 10,000 games = ~5 minutes
- This is ENOUGH for the small models we're training

### Testing the wrapper:

```python
# Quick sanity test:
env = KaggriculureGymEnv()
features = env.reset()
assert features.shape == (128,), f"Expected (128,), got {features.shape}"
assert features.dtype == np.float32

# Run one episode:
done = False
total_reward = 0
while not done:
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    features, reward, done, info = env.step(action)
    total_reward += reward

print(f"Episode done. Total reward: {total_reward}")
# Should be a large negative number (we did nothing, opponent played normally)
```

---

## 5. Upgrade 2: State Feature Extractor (128-dim)

### What to build:

```python
# File: D:/Kaggriculture/apex_next/ml_engine/feature_extractor.py

import numpy as np

def extract_features(obs):
    """
    Convert raw observation dict → 128-dim float32 feature vector.
    
    ALL features must come from the public observation dict.
    Zero hidden-state cheating. This is enforced by the Kaggle environment.
    
    Returns:
        np.array, shape (128,), dtype float32
    """
    features = np.zeros(128, dtype=np.float32)
    
    step = int(obs.get("step", 0))
    farms = obs.get("farms") or [{}, {}]
    our_farm = farms[0] if len(farms) > 0 else {}
    opp_farm = farms[1] if len(farms) > 1 else {}
    priv = obs.get("private") or {}
    shed = priv.get("shed") or {}
    mkt = obs.get("market") or {}
    prices = mkt.get("prices") or {}
    
    # ─── GROUP 1: TIME (4 dims) ───
    features[0] = step / 720.0                           # normalized step
    features[1] = (step // 24) / 30.0                    # normalized day
    features[2] = (step % 24) / 24.0                     # normalized hour
    features[3] = 1.0 - (step / 720.0)                   # fraction remaining
    
    # ─── GROUP 2: OUR ECONOMY (12 dims) ───
    money = float(our_farm.get("money", 0))
    features[4] = money / 10000.0                        # normalized cash
    features[5] = min(money / 2000.0, 1.0)               # can-afford-land indicator
    unlocked = our_farm.get("unlocked_quadrants") or ["NW"]
    features[6] = len(unlocked) / 4.0                    # quadrants fraction
    animals = our_farm.get("animals") or {}
    n_cows = int(animals.get("COW", 0))
    n_sheep = int(animals.get("SHEEP", 0))
    features[7] = n_cows / 14.0                          # normalized cows
    features[8] = n_sheep / 14.0                         # normalized sheep
    features[9] = (n_cows + n_sheep) / 14.0              # total animals
    workers = our_farm.get("workers") or []
    features[10] = len(workers) / 13.0                   # normalized worker count
    features[11] = 0.0  # idle workers (computed from worker states if available)
    n_idle = sum(1 for w in workers if not w.get("carrying"))
    features[11] = n_idle / max(len(workers), 1)
    features[12] = float(len(unlocked) >= 3)             # max quadrants reached
    features[13] = min(money / 500.0, 1.0)               # emergency liquidity flag
    features[14] = 0.0  # reserved
    features[15] = 0.0  # reserved
    
    # ─── GROUP 3: OUR SHED INVENTORY (12 dims) ───
    products = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                "MILK", "WOOL", "EGG", "FERTILIZER",
                "WHEAT_SEEDS", "CARROT_SEEDS", "STRAWBERRY_SEEDS"]
    for i, prod in enumerate(products):
        features[16 + i] = min(int(shed.get(prod, 0)) / 20.0, 1.0)
    
    # ─── GROUP 4: MARKET PRICES (16 dims) ───
    price_products = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY",
                      "MELON", "MILK", "WOOL", "FERTILIZER"]
    default_prices = [10, 20, 50, 120, 80, 193, 150, 100]
    for i, (prod, default_p) in enumerate(zip(price_products, default_prices)):
        p = float(prices.get(prod, default_p))
        features[28 + i] = p / (default_p * 2.0)        # normalized price
        features[36 + i] = (p - default_p) / default_p  # price deviation from default
    
    # ─── GROUP 5: OUR FARM TILES (16 dims) ───
    tiles = our_farm.get("tiles") or []
    n_tilled = 0
    n_planted = 0
    n_watered = 0
    n_mature = 0
    crop_counts = {"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0}
    for tile in tiles:
        if isinstance(tile, dict):
            if tile.get("tilled"): n_tilled += 1
            crop = tile.get("crop")
            if crop:
                n_planted += 1
                if crop in crop_counts: crop_counts[crop] += 1
                if tile.get("stage") == "RIPE": n_mature += 1
            if tile.get("watered"): n_watered += 1
    max_tiles = max(len(tiles), 1)
    features[44] = n_tilled / max_tiles
    features[45] = n_planted / max_tiles
    features[46] = n_watered / max_tiles
    features[47] = n_mature / max_tiles
    features[48] = crop_counts["STRAWBERRY"] / 34.0
    features[49] = crop_counts["MELON"] / 12.0
    features[50] = crop_counts["WHEAT"] / 10.0
    features[51] = crop_counts["TOMATO"] / 8.0
    features[52] = crop_counts["CARROT"] / 8.0
    features[53] = 0.0  # reserved
    features[54] = 0.0  # reserved
    features[55] = 0.0  # reserved
    # Pasture info
    features[56] = float(len(unlocked) >= 1)  # has NW
    features[57] = float(len(unlocked) >= 2)  # has NE
    features[58] = float(len(unlocked) >= 3)  # has SW
    features[59] = 0.0  # reserved
    
    # ─── GROUP 6: OPPONENT PUBLIC STATE (24 dims) ───
    # This is the KEY information for the opponent classifier
    opp_money = float(opp_farm.get("money", 0))
    opp_unlocked = opp_farm.get("unlocked_quadrants") or ["NW"]
    opp_animals = opp_farm.get("animals") or {}
    opp_cows = int(opp_animals.get("COW", 0))
    opp_sheep = int(opp_animals.get("SHEEP", 0))
    opp_workers = opp_farm.get("workers") or []
    opp_tiles = opp_farm.get("tiles") or []
    
    features[60] = opp_money / 10000.0
    features[61] = len(opp_unlocked) / 4.0
    features[62] = opp_cows / 14.0
    features[63] = opp_sheep / 14.0
    features[64] = (opp_cows + opp_sheep) / 14.0
    features[65] = len(opp_workers) / 13.0
    
    # Opponent crop analysis
    opp_crops = {"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0}
    opp_planted = 0
    opp_mature = 0
    for tile in opp_tiles:
        if isinstance(tile, dict):
            crop = tile.get("crop")
            if crop:
                opp_planted += 1
                if crop in opp_crops: opp_crops[crop] += 1
                if tile.get("stage") == "RIPE": opp_mature += 1
    
    features[66] = opp_planted / max(len(opp_tiles), 1)
    features[67] = opp_mature / max(len(opp_tiles), 1)
    features[68] = opp_crops["STRAWBERRY"] / 34.0
    features[69] = opp_crops["MELON"] / 12.0
    features[70] = opp_crops["WHEAT"] / 10.0
    features[71] = opp_crops["TOMATO"] / 8.0
    features[72] = opp_crops["CARROT"] / 8.0
    
    # Opponent economy ratios
    features[73] = opp_money / max(money, 1.0)          # relative cash
    features[74] = (opp_cows + opp_sheep) / max(n_cows + n_sheep, 1)  # relative animals
    features[75] = len(opp_workers) / max(len(workers), 1)  # relative workers
    features[76] = len(opp_unlocked) / max(len(unlocked), 1)  # relative land
    features[77] = 0.0  # reserved
    features[78] = 0.0  # reserved
    features[79] = 0.0  # reserved
    
    # Opponent strategy signals
    features[80] = float(opp_cows > opp_sheep * 2)      # cow-heavy signal
    features[81] = float(opp_sheep > opp_cows * 2)      # sheep-heavy signal
    features[82] = float(opp_planted > 20)               # crop-heavy signal
    features[83] = float(len(opp_unlocked) > len(unlocked))  # expanding faster
    
    # ─── GROUP 7: DERIVED STRATEGIC FEATURES (24 dims) ───
    # Wealth estimate (cash + inventory × prices)
    our_wealth = money
    for prod in ["STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "CARROT"]:
        our_wealth += int(shed.get(prod, 0)) * float(prices.get(prod, 0))
    
    features[84] = our_wealth / 100000.0                 # our estimated wealth
    features[85] = float(our_wealth > opp_money * 1.2)   # ahead economically
    features[86] = float(step > 500)                     # late game flag
    features[87] = float(step > 650)                     # endgame flag
    features[88] = float(n_cows + n_sheep >= 10)         # animal saturation
    features[89] = float(money < 200 and step < 200)     # early liquidity risk
    
    # Production efficiency signals
    milk_value = int(shed.get("MILK", 0)) * float(prices.get("MILK", 193))
    straw_value = int(shed.get("STRAWBERRY", 0)) * float(prices.get("STRAWBERRY", 120))
    features[90] = milk_value / 5000.0
    features[91] = straw_value / 5000.0
    features[92] = float(int(shed.get("MILK", 0)) > 4)  # milk accumulating (sell signal)
    features[93] = float(int(shed.get("STRAWBERRY", 0)) > 4)  # straw accumulating
    
    # Time pressure signals
    features[94] = max(0, (720 - step) / 720.0)         # urgency
    features[95] = float(step >= 700)                    # terminal liquidation zone
    features[96] = float(step == 71)                     # liquidity rescue step
    features[97] = float((step % 24) == 22)              # hour-22 sell window
    features[98] = float((step % 24) == 23)              # hour-23 clearance
    
    # Market opportunity signals
    straw_price = float(prices.get("STRAWBERRY", 120))
    milk_price = float(prices.get("MILK", 193))
    features[99] = float(straw_price > 140)              # strawberry price high
    features[100] = float(straw_price < 100)             # strawberry price low
    features[101] = float(milk_price > 200)              # milk price high
    features[102] = float(milk_price < 150)              # milk price low
    
    # Reserved for future features
    features[103:128] = 0.0
    
    return features
```

### Feature verification test:

```python
# Test with a real game observation:
env = KaggriculureGymEnv()
features = env.reset()
assert features.shape == (128,)
assert not np.any(np.isnan(features))
assert not np.any(np.isinf(features))
assert features[0] == 0.0  # step 0
assert 0 <= features[4]    # cash is non-negative
print("Feature extractor: PASS")
```

---

## 6. Upgrade 3: Opponent Classifier (Layer 3)

### Architecture:

```python
# File: D:/Kaggriculture/apex_next/ml_engine/models/opponent_classifier.py

import torch
import torch.nn as nn

class OpponentClassifier(nn.Module):
    """
    Classifies opponent into 5 archetype categories from public farm state.
    
    Input: 24 features (features[60:84] from the state extractor)
    Output: 5-class probability distribution
    
    Archetypes:
        0 = LIVESTOCK_HEAVY  (many animals, few crops)
        1 = CROP_HEAVY       (many strawberries/melons, few animals)
        2 = BALANCED          (standard mixed economy)
        3 = AGGRESSIVE_EXPAND (early land purchases, fast scaling)
        4 = MARKET_MANIPULATOR (unusual sell/buy patterns)
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(24, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 5),
        )
    
    def forward(self, x):
        """x: (batch, 24) → (batch, 5) logits"""
        return self.net(x)
    
    def predict(self, features_128):
        """
        Convenience method for inference in submission.py.
        Takes full 128-dim features, extracts opponent slice.
        """
        with torch.no_grad():
            opp_feats = torch.tensor(features_128[60:84], dtype=torch.float32).unsqueeze(0)
            logits = self.forward(opp_feats)
            probs = torch.softmax(logits, dim=1)
            return probs.squeeze(0).numpy()  # shape (5,)
```

### Training data preparation:

```python
# Generate labels from the 807 live match replays:
# 1. Parse each match using apex_next/lab/telemetry_ingestor.py
# 2. At each step, extract opponent features (features[60:84])
# 3. Label based on opponent's final farm composition:
#    - If opponent cows+sheep > 8: LIVESTOCK_HEAVY
#    - If opponent strawberry_tiles > 20: CROP_HEAVY
#    - If opponent land_count > our land_count at step 200: AGGRESSIVE_EXPAND
#    - Otherwise: BALANCED

# Training:
# - Cross-entropy loss
# - Adam optimizer, lr=1e-3
# - 100 epochs
# - 80/20 train/val split
# - Target: >70% validation accuracy
```

### Size: ~2,800 parameters (24×64 + 64 + 64×32 + 32 + 32×5 + 5)

---

## 7. Upgrade 4: Strategy Selector — PPO (Layer 2)

### Architecture:

```python
# File: D:/Kaggriculture/apex_next/ml_engine/models/strategy_selector.py

import torch
import torch.nn as nn

class StrategySelector(nn.Module):
    """
    Chooses blend weights for the 4 existing strategy profiles.
    
    Input: 133 dims (128 game features + 5 opponent archetype probs)
    Output: 4 strategy weights (softmax) + 1 confidence scalar (sigmoid)
    
    Strategy profiles (from submission.py DEFAULT_STRATEGY):
        0 = PREMIUM    (8 cows, 6 sheep, $250 reserve)
        1 = LIVESTOCK   (12 cows, 2 sheep, $150 reserve)
        2 = WHEAT_RUSH  (fast cash, 1 animal cap)
        3 = BALANCED     (standard play)
    """
    def __init__(self):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(133, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.strategy_head = nn.Linear(32, 4)   # strategy weights
        self.confidence_head = nn.Linear(32, 1)  # confidence scalar
        self.value_head = nn.Linear(32, 1)       # value function for PPO
    
    def forward(self, x):
        """x: (batch, 133) → strategy_weights, confidence, value"""
        h = self.shared(x)
        strategy_logits = self.strategy_head(h)
        strategy_weights = torch.softmax(strategy_logits, dim=1)  # (batch, 4)
        confidence = torch.sigmoid(self.confidence_head(h))        # (batch, 1)
        value = self.value_head(h)                                 # (batch, 1)
        return strategy_weights, confidence, value
    
    def select_strategy(self, features_128, opp_probs_5):
        """
        Inference for submission.py.
        Returns (strategy_weights, confidence) or None if low confidence.
        """
        with torch.no_grad():
            x = torch.tensor(
                np.concatenate([features_128, opp_probs_5]),
                dtype=torch.float32
            ).unsqueeze(0)
            weights, conf, _ = self.forward(x)
            weights = weights.squeeze(0).numpy()  # (4,)
            conf = conf.item()
            if conf < 0.60:
                return None  # fallback to APEX 4.0 defaults
            return weights, conf
```

### How strategy weights are applied in the agent:

```python
# In the modified agent() function:
weights = strategy_selector.select_strategy(features, opp_probs)
if weights is not None:
    w = weights[0]  # (4,) array: [premium, livestock, wheat_rush, balanced]
    
    # Interpolate strategy parameters:
    STRATEGY["cows"] = int(w[0]*8 + w[1]*12 + w[2]*12 + w[3]*8)
    STRATEGY["sheep"] = int(w[0]*6 + w[1]*2 + w[2]*2 + w[3]*6)
    STRATEGY["cash_reserve"] = int(w[0]*250 + w[1]*150 + w[2]*150 + w[3]*150)
    STRATEGY["animal_daily_cap"] = int(w[0]*3 + w[1]*3 + w[2]*1 + w[3]*3)
    # etc.
```

### PPO training:

```python
# Opponent pool for self-play:
opponents = [
    load_agent("D:/Kaggriculture/submission.py"),           # APEX 3.5
    load_agent("D:/Kaggriculture/APEX4_SUBMISSION_FINAL.py"), # APEX 4.0
    load_agent("D:/Kaggriculture/baseline/kaitofukami_v18.py"), # baseline
    random_strategy_agent(),                                  # random mix
]

# PPO hyperparameters:
config = {
    "n_episodes": 10000,
    "lr": 3e-4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_epsilon": 0.2,
    "epochs_per_update": 4,
    "batch_size": 64,
    "opponent_sampling": "uniform",  # randomly pick opponent each episode
}

# Reward: final (our_MCV - opponent_MCV) / 100000.0  (normalized)
```

### Size: ~10,400 parameters

---

## 8. Upgrade 5: Market Timing Optimizer (Layer 1)

### Architecture:

```python
# File: D:/Kaggriculture/apex_next/ml_engine/models/market_timer.py

import torch
import torch.nn as nn

class MarketTimer(nn.Module):
    """
    LSTM that observes price trajectories and outputs sell/hold signals.
    
    Input: 20-step price window × 8 price features = (20, 8) sequence
    Output: 4 products × 3 actions = 12 logits
    
    Products: STRAWBERRY, MILK, WOOL, MELON
    Actions:  SELL_NOW (0), HOLD (1), SELL_PARTIAL (2)
    """
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(input_size=8, hidden_size=32, batch_first=True)
        self.action_head = nn.Linear(32, 12)  # 4 products × 3 actions
        self.value_head = nn.Linear(32, 1)
    
    def forward(self, price_seq):
        """price_seq: (batch, 20, 8) → action_logits (batch, 12), value (batch, 1)"""
        _, (h_n, _) = self.lstm(price_seq)  # h_n: (1, batch, 32)
        h = h_n.squeeze(0)                   # (batch, 32)
        action_logits = self.action_head(h)  # (batch, 12)
        value = self.value_head(h)           # (batch, 1)
        return action_logits, value
    
    def get_signals(self, price_history):
        """
        Inference for submission.py.
        
        Args:
            price_history: list of dicts, last 20 steps of prices
            
        Returns:
            dict: {product: "SELL_NOW" | "HOLD" | "SELL_PARTIAL"}
        """
        # Build (1, 20, 8) tensor from price history
        products = ["STRAWBERRY", "MILK", "WOOL", "MELON",
                    "WHEAT", "CARROT", "TOMATO", "FERTILIZER"]
        seq = []
        for prices in price_history[-20:]:
            step_feats = [float(prices.get(p, 0)) / 200.0 for p in products]
            seq.append(step_feats)
        # Pad if less than 20 steps
        while len(seq) < 20:
            seq.insert(0, seq[0] if seq else [0.0]*8)
        
        with torch.no_grad():
            x = torch.tensor([seq], dtype=torch.float32)  # (1, 20, 8)
            logits, _ = self.forward(x)
            logits = logits.squeeze(0).reshape(4, 3)  # (4 products, 3 actions)
            actions = torch.argmax(logits, dim=1).numpy()
        
        action_map = {0: "SELL_NOW", 1: "HOLD", 2: "SELL_PARTIAL"}
        target_products = ["STRAWBERRY", "MILK", "WOOL", "MELON"]
        return {p: action_map[a] for p, a in zip(target_products, actions)}
```

### How market signals modify orders in the agent:

```python
# In the modified agent() function, AFTER base_agent generates market_orders:

signals = market_timer.get_signals(price_history)

modified_orders = []
for order in market_orders:
    if order[0] == "SELL":
        product = order[1]
        if product in signals:
            signal = signals[product]
            if signal == "HOLD":
                continue  # suppress this sell order
            elif signal == "SELL_PARTIAL":
                order[2] = max(1, order[2] // 2)  # sell half
            # else SELL_NOW: keep original order
    modified_orders.append(order)

act["market"] = modified_orders
```

### Size: ~5,300 parameters

---

## 9. Training Pipeline — Step by Step

```text
STEP 1: BUILD ENVIRONMENT WRAPPER
├── Create env_wrapper.py (Section 4)
├── Create feature_extractor.py (Section 5)
├── Test: run 10 episodes with PASS-only agent
├── Verify: features shape (128,), no NaN/Inf, valid ranges
├── Time: 1 hour
└── Output: working gym-like env

STEP 2: COLLECT EXPERT DEMONSTRATIONS
├── Run APEX 4.0 vs 4 different opponents (250 games each)
├── Save: {features, action, reward, opponent_features} per step
├── Total: 1,000 games × 720 steps = 720,000 transitions
├── Time: ~30 minutes on CPU
└── Output: D:/Kaggriculture/apex_next/ml_engine/data/current/step3g_targeted_1000/expert_demos_step3g_targeted_1000.npz

STEP 3: LABEL OPPONENT ARCHETYPES
├── For each of 1,000 games, classify opponent final state
├── Labeling rules (automated):
│   - COW+SHEEP > 8 at game end → LIVESTOCK_HEAVY
│   - STRAWBERRY tiles > 20 → CROP_HEAVY
│   - Land > our land at step 200 → AGGRESSIVE_EXPAND
│   - Unusual sell patterns → MARKET_MANIPULATOR
│   - Otherwise → BALANCED
├── Time: 5 minutes
└── Output: D:/Kaggriculture/apex_next/ml_engine/data/current/step3g_targeted_1000/opponent_labels_step3g_targeted_1000.npz

STEP 4: TRAIN OPPONENT CLASSIFIER (Layer 3)
├── Data: opponent features (24-dim) + labels (5 classes)
├── Split: 80% train / 20% validation
├── Loss: cross-entropy
├── Optimizer: Adam, lr=1e-3
├── Epochs: 100
├── Accept if: val accuracy > 70%
├── Time: 2 minutes on GPU
└── Output: D:/Kaggriculture/apex_next/ml_engine/checkpoints/opponent_classifier/opponent_classifier.pt

STEP 5: TRAIN STRATEGY SELECTOR (Layer 2) — PPO
├── Environment: KaggriculureGymEnv with diverse opponent pool
├── Agent: StrategySelector + APEX 4.0 execution
├── Reward: (our_MCV - opp_MCV) / 100000.0
├── Opponent pool: APEX 3.5, APEX 4.0, baseline, random variants
├── Episodes: 10,000
├── PPO config: lr=3e-4, gamma=0.99, clip=0.2, 4 epochs/update
├── Accept if: holdout WR > APEX 4.0 WR AND P05 >= APEX 4.0 P05
├── Time: ~30 minutes on GPU
└── Output: D:/Kaggriculture/apex_next/ml_engine/checkpoints/strategy_selector.pt

STEP 6: TRAIN MARKET TIMER (Layer 1) — PPO
├── Data: price trajectories from Step 2 expert demos
├── Reward: delta in sell revenue vs APEX 4.0 timing
├── Episodes: 5,000 (focused on market decisions only)
├── Accept if: avg revenue per sell order >= APEX 4.0 baseline
├── Time: ~15 minutes on GPU
└── Output: D:/Kaggriculture/apex_next/ml_engine/checkpoints/market_timer.pt

STEP 7: INTEGRATION TEST
├── Combine all 3 layers with APEX 4.0 base
├── Run 100 matches vs APEX 4.0 (head-to-head)
├── Run 100 matches vs APEX 3.5
├── Verify: 0 illegal actions, 0 crashes, valid action format
├── Time: ~10 minutes
└── Output: integration_test_report.json

STEP 8: FULL 4-GATE RELEASE VALIDATION
├── Gate 1: Exact replay on 46 loss seeds (WR >= 60%)
├── Gate 2: 200-scenario historical stress (WR >= 60%)
├── Gate 3: 100-match frozen holdout (WR >= 55%)
├── Gate 4: 6-dimension statistical judge (all pass)
├── Time: ~20 minutes
└── Output: APEX41_GATE_REPORT.json

STEP 9: PACKAGE FOR KAGGLE
├── Embed all 3 models as base64+gzip in submission.py
├── Total embedded size: ~20 KB compressed
├── Verify: standalone import, zero file dependencies
├── SHA256 hash and seal
├── Time: 5 minutes
└── Output: APEX41_HYBRID_SUBMISSION.py
```

Current artifact layout note, 2026-08-18:

The original plan above names simple flat output paths. The implemented
workspace now keeps artifacts in step-specific folders so current, pilot,
benchmark, and invalidated data cannot be confused:

```text
data/current/step3g_targeted_1000/
data/validation/step3g_targeted_validation_100/
data/pilots/
data/benchmarks/
data/invalidated/original_seat_bug/
checkpoints/opponent_classifier/
checkpoints/strategy_selector/
checkpoints/benchmarks/
evaluation/step1_environment/
evaluation/step3_diagnostics/
evaluation/step4_classifier/
evaluation/step5_strategy/
```

See `ARTIFACT_MAP.md` for the current navigation map.

---

## 10. Integration Into submission.py

### Where ML hooks into the existing agent:

```python
# Modified agent() function — lines 4464+ of the new submission

# At module level (loaded once):
import torch, gzip, base64, io
_OPP_MODEL = OpponentClassifier()
_STR_MODEL = StrategySelector()
_MKT_MODEL = MarketTimer()
# ... load weights from embedded base64 ...

_PRICE_HISTORY_BUFFER = []  # last 20 steps of prices

def agent(obs, configuration=None):
    global _PRICE_HISTORY_BUFFER
    
    # === EXISTING APEX 4.0 OBSERVATION PARSING (unchanged) ===
    step = obs["step"]
    farms = obs["farms"]
    # ... all existing parsing ...
    
    # === NEW: EXTRACT ML FEATURES ===
    features = extract_features(obs)  # 128-dim
    
    # === NEW: LAYER 3 — OPPONENT CLASSIFICATION ===
    opp_probs = _OPP_MODEL.predict(features)  # 5-dim
    
    # === NEW: LAYER 2 — STRATEGY SELECTION ===
    strategy_result = _STR_MODEL.select_strategy(features, opp_probs)
    if strategy_result is not None:
        weights, confidence = strategy_result
        # Interpolate strategy parameters (cow count, sheep count, etc.)
        _apply_strategy_blend(weights)
    
    # === EXISTING: RUN BASE AGENT (unchanged) ===
    act = _base_agent(obs)
    
    # === EXISTING: MARKET ORDER OVERLAYS (unchanged) ===
    market_orders = list(act.get("market") or [])
    # ... step 71 rescue, step 700+ clearance, etc ...
    
    # === NEW: LAYER 1 — MARKET TIMING ===
    _PRICE_HISTORY_BUFFER.append(obs["market"]["prices"])
    if len(_PRICE_HISTORY_BUFFER) > 20:
        _PRICE_HISTORY_BUFFER = _PRICE_HISTORY_BUFFER[-20:]
    
    if len(_PRICE_HISTORY_BUFFER) >= 5 and step < 700:
        signals = _MKT_MODEL.get_signals(_PRICE_HISTORY_BUFFER)
        market_orders = _apply_market_signals(market_orders, signals, shed)
    
    act["market"] = market_orders
    return act
```

### Safety invariants (NEVER violated by ML):

1. **Farmer actions**: ML NEVER modifies `act["farmer"]` or `act["hands"]`
2. **Pasture builds**: Steps 1 and 159 are hardwired (ML cannot override)
3. **Worker #0 cow pickup**: Step 170 is hardwired
4. **10-order market cap**: ML can only reduce orders, never add beyond 10
5. **Exception safety**: Entire ML block wrapped in try/except → fallback to APEX 4.0
6. **Confidence gating**: If any model has low confidence, skip ML entirely

---

## 11. Packaging for Kaggle

```python
# The final submission.py structure:

# 1. Standard library imports only (json, math, zlib, base64, io, struct)
# 2. PyTorch imported with fallback:
try:
    import torch
    import torch.nn as nn
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

# 3. Model class definitions (OpponentClassifier, StrategySelector, MarketTimer)
# 4. Embedded weights as base64+gzip string (~20 KB)
_WEIGHTS_B64 = "H4sIAAAAAAAAA..."

# 5. Weight loading (if torch available):
if _HAS_TORCH:
    _raw = gzip.decompress(base64.b64decode(_WEIGHTS_B64))
    _state = torch.load(io.BytesIO(_raw), weights_only=True)
    _OPP_MODEL = OpponentClassifier(); _OPP_MODEL.load_state_dict(_state["opp"])
    _STR_MODEL = StrategySelector(); _STR_MODEL.load_state_dict(_state["str"])
    _MKT_MODEL = MarketTimer(); _MKT_MODEL.load_state_dict(_state["mkt"])

# 6. Feature extractor function
# 7. Full APEX 4.0 agent code (4,635 lines, unchanged)
# 8. Modified agent() entry point with ML hooks
# 9. Graceful degradation: if _HAS_TORCH is False, runs pure APEX 4.0
```

### Important: Kaggle runtime DOES have PyTorch available.

---

## 12. Validation & Release Gates

Before deploying, the hybrid agent MUST pass the same 4-gate contract as APEX 4.0:

| Gate | Test | Threshold | How to Run |
|:---|:---|:---|:---|
| Gate 1 | Replay 46 loss seeds | WR >= 60% | `apex_next/lab/exact_replay_engine.py` |
| Gate 2 | 200 historical scenarios | WR >= 60% | `apex_next/lab/historical_suite_engine.py` |
| Gate 3 | 100 frozen holdout | WR >= 55% | `apex_next/lab/frozen_holdout_engine.py` |
| Gate 4 | 6-dim statistical judge | All pass | `apex_next/lab/statistical_judge.py` |

Additional hybrid-specific checks:
- **Torch-free fallback**: Agent runs correctly when PyTorch unavailable
- **Inference latency**: < 20ms mean, < 200ms max per step
- **Action validity**: 0 illegal actions across 1,000 test games
- **Regression check**: WR against APEX 4.0 >= 50% (doesn't get worse)

---

## 13. File Layout

```text
D:\Kaggriculture\apex_next\ml_engine\
├── README_ML_PLAN.md              ← THIS FILE
├── env_wrapper.py                 ← Upgrade 1: kaggle_environments wrapper
├── feature_extractor.py           ← Upgrade 2: 128-dim feature extraction
├── models/
│   ├── opponent_classifier.py     ← Upgrade 3: Layer 3 (supervised)
│   ├── strategy_selector.py       ← Upgrade 4: Layer 2 (PPO)
│   └── market_timer.py            ← Upgrade 5: Layer 1 (PPO + LSTM)
├── training/
│   ├── train_opponent_classifier.py
│   ├── train_strategy_selector.py
│   ├── train_market_timer.py
│   └── ppo_utils.py               ← PPO implementation
├── data/
│   ├── expert_demos.npz           ← Generated by Step 2
│   └── opponent_labels.npz        ← Generated by Step 3
├── checkpoints/
│   ├── opponent_classifier.pt
│   ├── strategy_selector.pt
│   └── market_timer.pt
├── tests/
│   ├── test_env_wrapper.py
│   ├── test_feature_extractor.py
│   └── test_integration.py
└── INVALIDATED/                   ← Old fake pipeline (quarantined)
    ├── README_INVALIDATED.md
    ├── training/
    ├── models/
    └── reports/
```

---

## 14. Hardware & Dependencies

| Resource | Available | Notes |
|:---|:---|:---|
| **GPU** | NVIDIA RTX 4050 (6GB VRAM) | Sufficient for all 3 models |
| **Python** | 3.13 | `C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe` |
| **PyTorch** | 2.6.0+cu124 | Already installed |
| **kaggle_environments** | Required | `pip install kaggle-environments` |
| **numpy** | Required | Already available |
| **Console** | Windows cp1252 | Avoid Unicode emojis in print() |

### Kaggle submission runtime:
- PyTorch IS available on Kaggle
- No GPU for inference (CPU only) — but our models are tiny (~18K params)
- No internet access — all weights must be embedded
- Single file submission only — everything in one `.py`

---

## 15. What NOT to Do

These are the exact mistakes the previous APEX 4.1 pipeline made:

| Mistake | What Happened | Correct Approach |
|:---|:---|:---|
| `np.random.randn()` as game states | Model learned random noise | Use `kaggle_environments` |
| Logistic formula for win/loss | Metrics were fictional | Measure actual game outcomes |
| CPU NumPy as "CUDA engine" | 95% of game mechanics missing | Use real `kaggle_environments` |
| Hardcoded `"PASS"` in validators | Self-deception | Run actual differential tests |
| `{"action": "APEX41_EXECUTE"}` | Invalid Kaggle format | Return `{"farmer":[], "hands":[], "market":[]}` |
| 256-dim random input, 8 random classes | No connection to game | 128-dim real features, meaningful outputs |
| Reporting fabricated metrics | Diverged from reality | Only report measured results |

---

## 16. Timeline

```text
Day 1 (4–6 hours):
  ├── Phase 1: Build env_wrapper.py + feature_extractor.py
  ├── Phase 2: Collect 1,000 expert demonstration games
  └── Phase 3: Train opponent classifier (Layer 3)

Day 2 (4–6 hours):
  ├── Phase 4: Train strategy selector with PPO (Layer 2)
  ├── Phase 5: Train market timer with PPO (Layer 1)
  └── Phase 6: Integration test (100 matches)

Day 3 (2–4 hours):
  ├── Phase 7: Full 4-gate release validation
  ├── Phase 8: Package into single submission.py
  └── Phase 9: Shadow test + seal

Total: ~12–16 hours of work across 3 days.
```
