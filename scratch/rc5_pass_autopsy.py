import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter, defaultdict
import submission_rc4_2_hybrid as rc42

path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]
opp_s0 = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

pass_by_hour = Counter()
pass_reasons = Counter()
unassigned_tasks_when_pass = Counter()
unmet_farm_needs_when_pass = Counter()

total_passes = 0
total_worker_actions = 0

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[1].observation
    day = obs["day"]
    hour = obs["hour"]
    
    # Run agent
    act = rc42.agent(obs)
    
    # Inspect workers
    farm = obs["farms"][1]
    workers = farm.get("workers", []) or farm.get("hands", []) or []
    positions = [farm.get("farmer", [4,4])] + workers
    num_units = len(positions)
    
    # Check what actions were emitted
    worker_acts = act.get("hands", []) if isinstance(act, dict) else []
    
    # Check farm state for unmet needs
    tiles = farm.get("tiles", [])
    unfed_animals = 0
    uncared_animals = 0
    unharvested_crops = 0
    unwatered_crops = 0
    available_fertilizer = 0
    
    for r in tiles:
        for t in r:
            if isinstance(t, dict):
                if t.get("animal") in ("COW", "SHEEP"):
                    if not t.get("fed_today", False): unfed_animals += 1
                    if not t.get("cared_today", False): uncared_animals += 1
                    if t.get("fertilizer_available", False): available_fertilizer += 1
                elif t.get("kind") == "PLANT":
                    if t.get("yield_units", 0) > 0: unharvested_crops += 1
                    if not t.get("watered_today", False): unwatered_crops += 1
                    
    for u_idx, w_act in enumerate(worker_acts):
        total_worker_actions += 1
        if not w_act or w_act[0] == "PASS":
            total_passes += 1
            pass_by_hour[hour] += 1
            
            # Record unmet needs during this PASS
            if unfed_animals > 0: unmet_farm_needs_when_pass["unfed_animals"] += 1
            if uncared_animals > 0: unmet_farm_needs_when_pass["uncared_animals"] += 1
            if unharvested_crops > 0: unmet_farm_needs_when_pass["unharvested_crops"] += 1
            if available_fertilizer > 0: unmet_farm_needs_when_pass["available_fertilizer"] += 1
            if unwatered_crops > 0: unmet_farm_needs_when_pass["unwatered_crops"] += 1
            if unfed_animals == 0 and uncared_animals == 0 and unharvested_crops == 0 and available_fertilizer == 0 and unwatered_crops == 0:
                unmet_farm_needs_when_pass["ALL_CHORES_COMPLETE"] += 1
                
    env.step([opp_s0[s], act])

print("=" * 80)
print(f"RC5-0 PASS AUTOPSY: TOTAL PASSES = {total_passes} / {total_worker_actions} ({total_passes/total_worker_actions*100:.1f}%)")
print("=" * 80)

print("\n1. PASS DISTRIBUTION BY HOUR OF THE DAY (0 to 23):")
print("-" * 60)
for h in range(24):
    bar = "#" * (pass_by_hour[h] // 5)
    period = "Night" if h < 6 or h >= 20 else ("Day Morning" if h < 12 else "Day Afternoon")
    print(f"  Hour {h:02d} ({period:<13}): {pass_by_hour[h]:>3} passes {bar}")

print("\n2. UNMET FARM NEEDS CO-OCCURRING WITH PASS ACTIONS:")
print("-" * 60)
for need, count in unmet_farm_needs_when_pass.most_common():
    print(f"  {need:<25}: {count:>4} passes co-occurred ({count/total_passes*100:.1f}%)")
print("=" * 80)
