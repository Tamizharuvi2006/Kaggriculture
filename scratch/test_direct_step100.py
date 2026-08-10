"""Directly invoke select_action on step 100 observation.
"""

from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import kaggle_environments
from apex.agent import _POLICY, WorldState, agent

def test_direct_step100():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 590244349})
    obs = env.reset()[0]["observation"]
    obs["step"] = 100
    obs["day"] = 4
    obs["hour"] = 4

    print("Calling agent(obs)...", flush=True)
    act = agent(obs)
    print("Result action:", act, flush=True)
    print("Telemetry traces:", len(_POLICY.telemetry_traces), flush=True)
    if _POLICY.telemetry_traces:
        t = _POLICY.telemetry_traces[0]
        print("Trace 0:", t.action_key, t.reasoning, flush=True)

if __name__ == "__main__":
    test_direct_step100()
