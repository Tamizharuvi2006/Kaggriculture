"""
Inspect planted tile dict structure when modified by actions
"""
import os
import sys
import json
import kaggle_environments

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import importlib.util
cand_path = os.path.join(_PROJECT_ROOT, "apex_next", "research", "EXP-0155", "candidate", "candidate_submission.py")
spec = importlib.util.spec_from_file_location("exp155", cand_path)
exp155_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp155_mod)
exp155_agent = exp155_mod.agent
from generalization_pipeline.submission_candidate_apex35 import agent as base_agent


def trace_planted_tile():
    env = kaggle_environments.make("kaggriculture")
    env.reset()
    
    # Run candidate vs base
    cand_env = env.run([exp155_agent, base_agent])
    
    for step_idx in [152, 160, 163, 164, 170, 200, 210, 211, 212]:
        if step_idx < len(cand_env):
            state = cand_env[step_idx][0]
            obs = state["observation"]
            farms = obs.get("farms", [])
            if farms:
                p0 = farms[0]
                tiles = p0.get("tiles", [])
                t73 = tiles[7][3] if len(tiles) > 7 and len(tiles[7]) > 3 else None
                print(f"Step {step_idx:03d} | Tile (7, 3): {t73}")


if __name__ == "__main__":
    trace_planted_tile()
