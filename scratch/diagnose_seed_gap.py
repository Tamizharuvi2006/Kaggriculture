import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42

path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]

# Champion analysis
champ_steps = [s[0] for s in steps]
opp_steps = [s[1] for s in steps]

print("=" * 80)
print("DIAGNOSING THE $126,924 PERFORMANCE GAP ON SEED 91697084")
print("=" * 80)

# Check Opponent strawberry exposure on Day 11
opp_d11 = opp_steps[264]["observation"]["farms"][1]
opp_straws = sum(1 for r in opp_d11["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
print(f"Opponent Strawberry Count on Day 11: {opp_straws}")

# Check Champion Day 11 farm
champ_d11 = champ_steps[264]["observation"]["farms"][0]
champ_straws = sum(1 for r in champ_d11["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
champ_cows = sum(1 for r in champ_d11["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "COW")
champ_sheeps = sum(1 for r in champ_d11["tiles"] for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
champ_money_d11 = champ_d11["money"]
print(f"Champion Day 11: Strawberries={champ_straws}, Cows={champ_cows}, Sheep={champ_sheeps}, Money=${champ_money_d11:,.0f}")

# Check RC4.2 run on same seed
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()
rc42_confirm_day = None
for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[0].observation
    day = obs["day"]
    hour = obs["hour"]
    act = rc42.agent(obs)
    if rc42._FLOOD_CONFIRMED and rc42_confirm_day is None:
        rc42_confirm_day = (day, hour)
    env.step([act, opp_steps[s+1]["action"]])

rc42_d30 = env.state[0].observation["farms"][0]
print(f"RC4.2 Confirmation: {rc42_confirm_day}")
print(f"RC4.2 Day 30 Final Money: ${rc42_d30['money']:,.0f}")
print("=" * 80)
