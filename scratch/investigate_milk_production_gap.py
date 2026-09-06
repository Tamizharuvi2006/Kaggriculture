import json

path_champ = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"

with open(path_champ, "r", encoding="utf-8") as f:
    rep = json.load(f)

steps = rep["steps"]
seat = 0 # The $146,972 champion is seat 0

print("=" * 80)
print("INVESTIGATING THE $146K CHAMPION: LIVESTOCK TIMELINE & HARVEST FORENSICS")
print("=" * 80)

# Track when pastures were built, when animals were placed, how many feeds, how many milks
pastures_built = 0
cows_placed = []
milks_harvested = 0
wools_harvested = 0
feeds_executed = 0

for step_idx in range(1, len(steps)):
    obs = steps[step_idx][seat]["observation"]
    day = obs["day"]
    hour = obs["hour"]
    act = steps[step_idx][seat].get("action", {})
    
    if isinstance(act, dict):
        for worker_act in act.get("workers", []):
            if not worker_act: continue
            cmd = worker_act[0] if len(worker_act) > 0 else ""
            if cmd == "PLACE" and len(worker_act) > 1:
                item = worker_act[1]
                if item == "COW":
                    cows_placed.append((day, hour, step_idx))
            elif cmd == "FEED":
                feeds_executed += 1
            elif cmd == "MILK":
                milks_harvested += 1
            elif cmd == "SHEAR":
                wools_harvested += 1

print(f"Total MILK actions executed:  {milks_harvested}")
print(f"Total SHEAR actions executed: {wools_harvested}")
print(f"Total FEED actions executed:  {feeds_executed}")
print(f"Total Cows Placed: {len(cows_placed)}")
print("Cows Placement Timeline (Day, Hour, Step):")
for cp in cows_placed:
    print(f"  Cow placed at Day {cp[0]:02d} Hour {cp[1]:02d} (Step {cp[2]})")

# Check worker count progression
print("-" * 80)
print("Worker Hires Timeline:")
for step_idx in range(1, len(steps)):
    act = steps[step_idx][seat].get("action", {})
    if isinstance(act, dict):
        for m in act.get("market", []):
            if m and m[0] == "HIRE":
                obs = steps[step_idx][seat]["observation"]
                print(f"  HIRE at Day {obs['day']:02d} Hour {obs['hour']:02d} (Step {step_idx})")
print("=" * 80)
