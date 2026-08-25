"""Inspect raw observation keys of Seed 66666 (Elite) vs Seed 90909 (Crash)."""
import os
import sys
import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 66666})
env.reset()
obs_elite = env.state[0].observation

env_crash = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 90909})
env_crash.reset()
obs_crash = env_crash.state[0].observation

print("=== SEED 66666 (ELITE: $277k) ===")
print("Market Prices at Step 0:", obs_elite.get("market", {}).get("prices", {}))
print("Market Inventory at Step 0:", obs_elite.get("market", {}).get("inventory", {}))
print("Town State at Step 0:", obs_elite.get("town", {}))

print("\n=== SEED 90909 (CRASH: $60k) ===")
print("Market Prices at Step 0:", obs_crash.get("market", {}).get("prices", {}))
print("Market Inventory at Step 0:", obs_crash.get("market", {}).get("inventory", {}))
print("Town State at Step 0:", obs_crash.get("town", {}))
