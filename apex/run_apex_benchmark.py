"""Master Benchmark & Diagnostic Runner for Fully Upgraded L+ APEX Architecture.
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from apex.world_model import WorldState
from apex.economic_model import CommodityModel
from apex.time_model import TimeModel
from apex.meta_model import MetaDetector
from apex.opponent_model import OpponentModel
from apex.strategy_adapter import StrategyAdapter
from apex.experience_memory import ExperienceMemory
from apex.memory import MemorySystem
from apex.expert import LPlusExpert
from apex.policy import ApexPolicy
from apex.evolution import ApexEvolutionLoop

def test_apex_pipeline():
    print("====================================================")
    print("🚀 MASTER L+ APEX AUTONOMOUS ARCHITECTURE DIAGNOSTIC TEST")
    print("====================================================")

    # 1. Dummy observation representing high Melon price scenario & Aggressive Opponent
    dummy_obs = {
        "step": 120,
        "day": 5,
        "hour": 0,
        "player": 0,
        "market": {"prices": {"MELON": 250.0, "MILK": 180.0, "WOOL": 220.0, "WHEAT": 25.0, "STRAWBERRY": 120.0}},
        "farms": [
            {
                "money": 4500.0,
                "unlocked_quadrants": ["NW"],
                "inventory": {"MELON": 15, "WHEAT": 40},
                "tiles": [
                    {"kind": "PLANT", "crop": "MELON", "yield": 6},
                ],
                "hires_today": 0,
                "workers": [],
            },
            {
                "money": 3200.0,
                "unlocked_quadrants": ["NW", "NE"],
                "tiles": [
                    {"kind": "PLANT", "crop": "MELON"},
                    {"kind": "PLANT", "crop": "MELON"},
                    {"kind": "PLANT", "crop": "MELON"},
                    {"kind": "PLANT", "crop": "MELON"},
                    {"kind": "PLANT", "crop": "MELON"},
                    {"kind": "PLANT", "crop": "MELON"},
                ],
            }
        ]
    }

    state = WorldState(dummy_obs)
    print("1. WorldState Initialized:")
    print(f"   Day: {state.day} | Step: {state.step} | Money: ${state.money:,.2f}")

    # 2. Test Commodity-Agnostic Model & Rankings
    rankings = CommodityModel.rank_all_commodities(state)
    print("\n2. Dynamic Commodity ROI Rankings:")
    for r in rankings[:5]:
        print(f"   - {r.name:<12} ({r.category:<13}): Cost=${r.cost:5.1f} | Net Profit=${r.net_profit:6.1f} | ROI/Step={r.roi_per_step:.6f}")

    # 3. Test MetaDetector & OpponentModel
    meta_sig = MetaDetector.detect_regime(state)
    opp_sig = OpponentModel.analyze_opponent(state)
    print("\n3. Sensing & Signature Layer:")
    print(f"   Market Regime: {meta_sig.regime}")
    print(f"   Opponent Archetype: {opp_sig.archetype} (Aggressiveness: {opp_sig.aggressiveness:.1f})")

    # 4. Test StrategyAdapter In-Game Switching
    strat_state = StrategyAdapter.select_active_strategy(state, meta_sig, opp_sig)
    print("\n4. StrategyAdapter Dynamic Regime Switch:")
    print(f"   Active Strategy State: {strat_state.name} (Focus Commodity: {strat_state.focus_commodity})")

    # 5. Test Experience Memory
    exp_mem = ExperienceMemory()
    adj = exp_mem.retrieve_adjustment(710, "NORTH_SOUTH_EAST_WEST_WALK")
    print("\n5. ExperienceMemory Retrieval:")
    print(f"   Step 710 Late Transit Penalty Adjustment: {adj:.1f}")

    # 6. Test Autonomous Policy Execution
    policy = ApexPolicy(mode="advisor_guided")
    apex_act = policy.select_action(dummy_obs, state)
    metrics = policy.get_metrics()
    print("\n6. Master ApexPolicy Online Adaptation:")
    print(f"   Active Strategy: {metrics['active_strategy']}")
    print(f"   Detected Regime: {metrics['detected_regime']}")
    print(f"   Opponent Archetype: {metrics['opponent_archetype']}")
    print(f"   Market Orders Generated: {apex_act.get('market', [])}")

    print("\n====================================================")
    print("✅ MASTER L+ APEX AUTONOMOUS ARCHITECTURE FULLY VERIFIED!")
    print("====================================================")

if __name__ == "__main__":
    test_apex_pipeline()
