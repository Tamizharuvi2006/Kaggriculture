"""Representative Kaggle Population Suite: Stratified multi-archetype opponent benchmark."""
from __future__ import annotations
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def _load_module(rel_path: str, mod_name: str):
    full_path = os.path.join(BASE_DIR, rel_path)
    spec = importlib.util.spec_from_file_location(mod_name, full_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# 1. Tier 1 (900-1200: Foundation & Narrow Archetypes)
v18_mod = _load_module(os.path.join("baseline", "kaitofukami-v18.py"), "mod_v18")
challengers_mod = _load_module(os.path.join("baseline", "challengers.py"), "mod_challengers")

# 2. Tier 2 (1200-1400: Dynamic Ladder Competitors)
v81_mod = _load_module(os.path.join("baseline", "submission_v81.py"), "mod_v81")
v82_mod = _load_module(os.path.join("baseline", "submission_v82.py"), "mod_v82")

# 3. Tier 3 (1400-1800: High-Yield Agro & Opponent-Aware Policies)
v83_mod = _load_module(os.path.join("baseline", "submission_v83.py"), "mod_v83")
v83_oa_mod = _load_module(os.path.join("baseline", "submission_v83_opponent_aware.py"), "mod_v83_oa")
cows12_mod = _load_module(os.path.join("baseline", "submission_v81_cows12.py"), "mod_cows12")
cows13_mod = _load_module(os.path.join("baseline", "submission_v82_cows13.py"), "mod_cows13")

# 4. Tier 4 (1800+: Multi-Asset Experimental Policies)
v84_mod = _load_module(os.path.join("baseline", "submission_v84_experimental.py"), "mod_v84")

POPULATION_SUITE = {
    # Tier 1 (900-1200)
    "T1_v18_mirror": {
        "tier": "900-1200 (Foundation)",
        "archetype": "Mirror Saturated Strawberry Control",
        "agent": v18_mod.agent,
    },
    "T1_carrot_rusher": {
        "tier": "900-1200 (Foundation)",
        "archetype": "Early Fast-Cash Carrot Rusher",
        "agent": challengers_mod.carrot_rusher_agent,
    },
    "T1_livestock_rusher": {
        "tier": "900-1200 (Foundation)",
        "archetype": "Early Livestock / Milk Rusher",
        "agent": challengers_mod.livestock_rusher_agent,
    },

    # Tier 2 (1200-1400)
    "T2_dynamic_v81": {
        "tier": "1200-1400 (Dynamic Ladder)",
        "archetype": "Dynamic Market Liquidator",
        "agent": v81_mod.agent,
    },
    "T2_rebound_v82": {
        "tier": "1200-1400 (Dynamic Ladder)",
        "archetype": "Market Rebound Timer",
        "agent": v82_mod.agent,
    },

    # Tier 3 (1400-1800)
    "T3_high_yield_v83": {
        "tier": "1400-1800 (High-Yield Agro)",
        "archetype": "High-Yield Strawberry Agro Engine",
        "agent": v83_mod.agent,
    },
    "T3_opponent_aware_v83": {
        "tier": "1400-1800 (High-Yield Agro)",
        "archetype": "Adversarial Opponent-Aware Policy",
        "agent": v83_oa_mod.agent,
    },
    "T3_cows12_herd": {
        "tier": "1400-1800 (High-Yield Agro)",
        "archetype": "12-Cow Dual-Asset Mixed Engine",
        "agent": cows12_mod.agent,
    },
    "T3_cows13_herd": {
        "tier": "1400-1800 (High-Yield Agro)",
        "archetype": "13-Cow High-Capacity Livestock Engine",
        "agent": cows13_mod.agent,
    },

    # Tier 4 (1800+)
    "T4_experimental_v84": {
        "tier": "1800+ (Multi-Asset Elite)",
        "archetype": "Multi-Asset Scaled Experimental Engine",
        "agent": v84_mod.agent,
    },
}
