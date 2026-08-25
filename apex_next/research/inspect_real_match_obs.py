"""
Inspect Real Match Observation Schema during APEX 3.5 Match
"""
import kaggle_environments
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.research.match_runner import _load_agent, BASELINE_PATH

agent_mod = _load_agent(BASELINE_PATH, "base")

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()

recorded_obs = []

def tracking_agent(obs):
    if len(recorded_obs) < 5:
        recorded_obs.append(obs)
    return agent_mod.agent(obs)

env.run([tracking_agent, agent_mod.agent])

obs = recorded_obs[2]  # Step 2
print("=== KEYS IN REAL OBS ===")
print(list(obs.keys()))
print("Player index:", obs.get("player"))

farms = obs.get("farms", [])
print(f"Farms count: {len(farms)}")
for p_idx, f in enumerate(farms):
    print(f"\n--- Farm {p_idx} ---")
    for k, v in f.items():
        if k == "tiles":
            non_empty = sum(1 for row in v for cell in row if cell is not None and cell != "LOCKED")
            print(f"  tiles: {len(v)}x{len(v[0])} grid with {non_empty} active tiles")
            # print sample active tile
            for r_idx, row in enumerate(v):
                for c_idx, cell in enumerate(row):
                    if cell is not None and cell != "LOCKED":
                        print(f"    tile ({r_idx},{c_idx}): {cell}")
                        break
                if non_empty > 0: break
        else:
            print(f"  {k}: {v}")

print("\n=== PRIVATE SHED ===")
print(obs.get("private"))

print("\n=== TOWN ===")
print(obs.get("town"))

print("\n=== MARKET ===")
print(obs.get("market"))
