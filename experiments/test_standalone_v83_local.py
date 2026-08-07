"""Local Kaggle Environment Validation for submission_v83_standalone.py."""

import sys
import os
import importlib.util
import kaggle_environments

sub_path = os.path.join(os.path.dirname(__file__), "..", "baseline", "submission_v83_standalone.py")
spec = importlib.util.spec_from_file_location("sub_v83_standalone", sub_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent = mod.agent

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1000})
state = env.run([agent, agent])
score0 = float(state[-1][0]["observation"]["farms"][0]["money"])
score1 = float(state[-1][1]["observation"]["farms"][1]["money"])

print(f"Validation Game Completed Cleanly! Score 0: ${score0:,.2f} | Score 1: ${score1:,.2f}")
