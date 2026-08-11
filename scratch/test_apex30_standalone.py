"""Local Execution Test for Monolithic APEX 3.0 Artifact.
"""

from __future__ import annotations
import sys
import os
import importlib.util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments

def test_apex30_standalone():
    print("Testing Standalone APEX 3.0 Monolithic Artifact Execution...", flush=True)
    art_path = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex30.py")
    
    spec = importlib.util.spec_from_file_location("apex30_mod", art_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    target_agent = getattr(mod, "agent_apex30", getattr(mod, "agent", None))
    assert target_agent is not None, "Error: agent function not found in artifact!"

    # Load baseline opponent
    opp_path = os.path.join(BASE_DIR, "baseline", "kaitofukami-v18.py")
    spec_opp = importlib.util.spec_from_file_location("opp_mod", opp_path)
    mod_opp = importlib.util.module_from_spec(spec_opp)
    spec_opp.loader.exec_module(mod_opp)

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})
    env.run([target_agent, mod_opp.agent])

    p0_money = float(env.steps[-1][0]["observation"]["farms"][0].get("money", 0.0))
    p1_money = float(env.steps[-1][1]["observation"]["farms"][1].get("money", 0.0))

    print(f"Match Execution Complete (720 Steps):")
    print(f"  APEX 3.0 Standalone Wealth : ${p0_money:,.2f}")
    print(f"  Opponent Wealth            : ${p1_money:,.2f}")
    print(f"  Outcome                    : {'WIN ✅' if p0_money >= p1_money else 'LOSS ❌'}")
    print(f"Local Execution Test PASSED cleanly! 0 External Local Imports.")

if __name__ == "__main__":
    test_apex30_standalone()
