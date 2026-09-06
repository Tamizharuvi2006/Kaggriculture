import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42

path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]
opp_s0 = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

# We will track every animal-day:
# An "animal-day" is one animal alive on one day.
# For each animal-day, we check at Hour 23:
# - Was it fed?
# - Was it cared?
# - Did it produce yield?

animal_days_total = 0
animal_days_fed = 0
animal_days_cared = 0
animal_days_yield_generated = 0
animal_days_yield_collected = 0

# Also track when each animal came into existence
animals_alive_by_day = Counter()

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[1].observation
    day = obs["day"]
    hour = obs["hour"]
    
    act = rc42.agent(obs)
    env.step([opp_s0[s], act])
    
    # At hour 23, audit all living animals
    if hour == 23:
        farm = env.state[1].observation["farms"][1]
        tiles = farm.get("tiles", [])
        for r in tiles:
            for t in r:
                if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"):
                    animal_days_total += 1
                    animals_alive_by_day[day] += 1
                    if t.get("fed_today", False): animal_days_fed += 1
                    if t.get("cared_today", False): animal_days_cared += 1
                    if t.get("yield_units", 0) > 0: animal_days_yield_generated += 1

print("=" * 80)
print("EXACT ACCOUNTING: PROBLEM A (CAPACITY) vs PROBLEM B (SERVICING)")
print("=" * 80)
print(f"Total Animal-Days in RC4.2: {animal_days_total}")
print(f"  Animal-Days FED:          {animal_days_fed} / {animal_days_total} ({animal_days_fed/animal_days_total*100:.1f}%)")
print(f"  Animal-Days CARED:        {animal_days_cared} / {animal_days_total} ({animal_days_cared/animal_days_total*100:.1f}%)")
print(f"  Animal-Days with Yield:   {animal_days_yield_generated} / {animal_days_total} ({animal_days_yield_generated/animal_days_total*100:.1f}%)")

print("\nLIVING HERD SIZE BY DAY (RC4.2):")
print("-" * 60)
for d in range(30):
    print(f"  Day {d:02d}: {animals_alive_by_day[d]:>2} animals alive")

# Compare to theoretical maximum if 12 animals existed from Day 0:
max_possible_animal_days = 12 * 30 # 360 animal-days
print("-" * 60)
print(f"Theoretical 12-Animal Capacity (Days 0-29): {max_possible_animal_days} animal-days")
print(f"Actual Animal-Days Realized by RC4.2:       {animal_days_total} animal-days ({animal_days_total/max_possible_animal_days*100:.1f}% of potential!)")
print(f"Lost Capacity due to Delayed Scaling:       {max_possible_animal_days - animal_days_total} animal-days ({(max_possible_animal_days - animal_days_total)/max_possible_animal_days*100:.1f}% LOST!)")
print("=" * 80)
