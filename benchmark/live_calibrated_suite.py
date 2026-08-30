"""EXP162 Live-Calibrated Population Benchmark Suite."""
from __future__ import annotations
import os
import sys
import json
import glob
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from benchmark.population_suite import POPULATION_SUITE

# Empirical Population Density Weights derived from the 129 Kaggle Replay Corpus
# Total = 100.0%
LIVE_CALIBRATED_DISTRIBUTION = {
    # 1. Strawberry / V18 Duopoly Clones (Observed: 48.8% +- 8.6%)
    "T1_v18_mirror": {
        "cluster_name": "Strawberry_Duopoly_Clones",
        "elo_band": "900-1100 (Core Meta)",
        "empirical_weight": 0.488,
        "ci_95": [0.402, 0.574],
        "agent": POPULATION_SUITE["T1_v18_mirror"]["agent"],
    },
    # 2. Dynamic Price-Responsive Agro Hybrids (Observed: 24.0% +- 7.4%)
    "T2_dynamic_v81": {
        "cluster_name": "Price_Responsive_Hybrids",
        "elo_band": "1100-1300 (Dynamic Intermediate)",
        "empirical_weight": 0.120,
        "ci_95": [0.075, 0.185],
        "agent": POPULATION_SUITE["T2_dynamic_v81"]["agent"],
    },
    "T2_rebound_v82": {
        "cluster_name": "Price_Responsive_Hybrids",
        "elo_band": "1100-1300 (Dynamic Intermediate)",
        "empirical_weight": 0.120,
        "ci_95": [0.075, 0.185],
        "agent": POPULATION_SUITE["T2_rebound_v82"]["agent"],
    },
    # 3. High-Yield Agro & Cattle Conglomerates (Observed: 15.5% +- 6.2%)
    "T3_cows12_herd": {
        "cluster_name": "Cattle_Agro_Conglomerates",
        "elo_band": "1300-1800 (Advanced Dairy/Agro)",
        "empirical_weight": 0.078,
        "ci_95": [0.041, 0.134],
        "agent": POPULATION_SUITE["T3_cows12_herd"]["agent"],
    },
    "T4_experimental_v84": {
        "cluster_name": "Cattle_Agro_Conglomerates",
        "elo_band": "1800+ (Multi-Asset Elite)",
        "empirical_weight": 0.077,
        "ci_95": [0.040, 0.133],
        "agent": POPULATION_SUITE["T4_experimental_v84"]["agent"],
    },
    # 4. Primitive Baselines & Legacy Rushers (Observed: 11.7% +- 5.5%)
    "T1_carrot_rusher": {
        "cluster_name": "Primitive_Legacy_Rushers",
        "elo_band": "Under 900 (Entry Level)",
        "empirical_weight": 0.058,
        "ci_95": [0.027, 0.111],
        "agent": POPULATION_SUITE["T1_carrot_rusher"]["agent"],
    },
    "T1_livestock_rusher": {
        "cluster_name": "Primitive_Legacy_Rushers",
        "elo_band": "Under 900 (Entry Level)",
        "empirical_weight": 0.059,
        "ci_95": [0.028, 0.112],
        "agent": POPULATION_SUITE["T1_livestock_rusher"]["agent"],
    },
}
