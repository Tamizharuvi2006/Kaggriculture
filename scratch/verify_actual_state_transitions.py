import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42

path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]

print("=" * 80)
print("GROUND-TRUTH STATE TRANSITIONS AUDIT: CHAMPION vs RC4.2")
print("=" * 80)

# 1. CHAMPION ACTUAL HARVESTED PRODUCTION (from step-by-step observation deltas)
champ_milk_collected = 0
champ_wool_collected = 0
champ_straw_collected = 0
champ_fert_collected = 0

prev_farm0 = steps[0][0]["observation"]["farms"][0]
for s in range(1, len(steps)):
    f0 = steps[s][0]["observation"]["farms"][0]
    # Check yield collections across tiles
    # In kaggriculture, when harvested/cared, tile yield decreases or shed/inventory increases
    # Let's track sales from market actions
    act0 = steps[s][0].get("action", {})
    # To get actual transactions, we observe shed + market executions
    
# Let's inspect final money and total items sold by Champion from engine observation
# In observation, does it track total sales? No, money tracks revenue!
# Let's run RC4.2 on the exact seed of episode-91697084 and compare final breakdown!
opp_actions = [steps[s][1].get("action") for s in range(1, len(steps))]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

rc42_milk_harvested = 0
rc42_wool_harvested = 0
rc42_fert_collected = 0
rc42_crops_harvested = Counter()

# Track successful actions by checking state transitions
for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[0].observation
    prev_shed = dict(obs.get("private", {}).get("shed", {}))
    prev_money = obs["farms"][0]["money"]
    
    act = rc42.agent(obs)
    env.step([act, opp_actions[s]])
    
    post_obs = env.state[0].observation
    post_shed = dict(post_obs.get("private", {}).get("shed", {}))
    
    # Check what items were produced or sold
    # When sold, shed decreases and money increases
    # When harvested/dropped, shed increases

final_rc42_money = env.state[0].observation["farms"][0]["money"]
print(f"Champion Final Money: ${steps[-1][0]['observation']['farms'][0]['money']:,.0f}")
print(f"RC4.2 Final Money:    ${final_rc42_money:,.0f}")
print(f"Performance Gap:      ${steps[-1][0]['observation']['farms'][0]['money'] - final_rc42_money:+,.0f}")
print("=" * 80)
