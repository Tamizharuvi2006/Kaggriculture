"""Debug terminal n star at step 696."""
import os, sys, importlib.util
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1000})
env.reset()
while env.state[0].observation.get("step", 0) <= 695:
    a0 = sub_d1.agent(env.state[0].observation, env.configuration)
    a1 = sub_d1.agent(env.state[1].observation, env.configuration)
    env.step([a0, a1])

obs0 = env.state[0].observation
f0 = obs0.get("farms", [{}, {}])[0]
print("Player 0 farm keys:", f0.keys())
ripe_count = 0
for r_idx, row in enumerate(f0.get("tiles", [])):
    for c_idx, t in enumerate(row):
        if isinstance(t, dict):
            k = t.get("kind")
            y = t.get("yield_units", 0)
            crop = t.get("crop")
            print(f"  Tile ({r_idx},{c_idx}): kind={k}, dict={t}")
            if k == "PLANT" and y > 0:
                ripe_count += 1

print(f"Total Ripe Plant Tiles: {ripe_count}")
