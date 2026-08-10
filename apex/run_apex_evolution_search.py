"""APEX 2.0 Autonomous Evolution Search & Gate 3 Qualification Harness.
"""

from __future__ import annotations
import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.evolution import ApexEvolutionLoop

SEEDS = [590244349, 855978439, 1745977583, 91286593]

def main():
    print("====================================================================================================")
    print("🧬 APEX 2.0 AUTONOMOUS EVOLUTION & GATE 3 META-QUALIFICATION SEARCH")
    print("====================================================================================================")

    ev_loop = ApexEvolutionLoop(seeds=SEEDS, ladder_benchmark_target=130000.0)
    
    # Evaluate APEX 2.0 Agent Monolith
    cand_path = os.path.join(BASE_DIR, "apex", "agent.py")
    results = ev_loop.evaluate_candidate(cand_path, "APEX_2.0_MASTER")

    print("\n📊 Gate Qualification Report:")
    print(json.dumps(results, indent=2))

    print("\n====================================================================================================")
    if results["gate3_meta_qualify"]:
        print("🏆 GATE 3 META-QUALIFICATION PASSED! APEX 2.0 IS QUALIFIED FOR COMPETITIVE SUBMISSION!")
    elif results["gate1_replay_pass"]:
        print("✅ GATE 1 & GATE 2 REPLAY REPRODUCTION PASSED WITH 100% SAFETY!")
    else:
        print("⚠️ GATE AUDIT INCOMPLETE")
    print("====================================================================================================")

if __name__ == "__main__":
    main()
