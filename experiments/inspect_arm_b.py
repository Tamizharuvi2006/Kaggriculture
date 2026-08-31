"""Inspect exact Day 29 discrepancy between Arm B and Arm C on Seed 90012."""
import os, sys, importlib.util
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import kaggle_environments
from benchmark.live_calibrated_suite import LIVE_CALIBRATED_DISTRIBUTION

spec_d1 = importlib.util.spec_from_file_location("sub_d1", os.path.join(BASE_DIR, "submission_clean.py"))
sub_d1 = importlib.util.module_from_spec(spec_d1)
spec_d1.loader.exec_module(sub_d1)

opp_fn = LIVE_CALIBRATED_DISTRIBUTION["T1_v18_mirror"]["agent"]

# Run Arm B on Seed 90012
env_b = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 90012})
env_b.reset()
while env_b.state[0].observation.get("step", 0) <= 695:
    o0 = env_b.state[0].observation
    o1 = env_b.state[1].observation
    a0 = sub_d1.agent(o0, env_b.configuration)
    try: a1 = opp_fn(o1, env_b.configuration)
    except TypeError: a1 = opp_fn(o1)
    env_b.step([a0, a1])

print("\n--- ARM B STEP 696 TO 700 ---")
for s in range(696, 705):
    o0 = env_b.state[0].observation
    o1 = env_b.state[1].observation
    act0_raw = sub_d1._base_agent(o0)
    if s == 696:
        m = act0_raw.get("market", []) or []
        m_clean = [o for o in m if not (isinstance(o, (list, tuple)) and len(o) >= 1 and o[0] == "HIRE")]
        for _ in range(10): m_clean.append(["HIRE"])
        act0 = {"farmer": act0_raw.get("farmer", ["PASS"]), "hands": act0_raw.get("hands", []), "market": m_clean[:10]}
    else:
        act0 = act0_raw
    print(f"Step {s}: Arm B act0 market = {act0.get('market')}, farmer={act0.get('farmer')}, shed={o0.get('private', {}).get('inventories', [{}])[0]}")
    try: a1 = opp_fn(o1, env_b.configuration)
    except TypeError: a1 = opp_fn(o1)
    env_b.step([act0, a1])
