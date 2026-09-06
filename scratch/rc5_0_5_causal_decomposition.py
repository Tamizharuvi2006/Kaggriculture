import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter, defaultdict
import submission_rc4_2_hybrid as rc42

path_champ = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(path_champ, "r", encoding="utf-8") as f:
    rep = json.load(f)

steps = rep["steps"]
opp_actions = [steps[s][1].get("action") for s in range(1, len(steps))]

# 1. PROFILE CHAMPION (SEAT 0)
champ_milestones = {}
champ_cows_placed = Counter()
champ_sheep_placed = Counter()
champ_pastures_built = Counter()
champ_actions_cum = Counter()

# Track champion step by step
for s in range(1, len(steps)):
    f0 = steps[s][0]["observation"]["farms"][0]
    day = steps[s][0]["observation"]["day"]
    hour = steps[s][0]["observation"]["hour"]
    act = steps[s][0].get("action", {})
    
    if isinstance(act, dict):
        for h in act.get("hands", []):
            if h:
                champ_actions_cum[h[0]] += 1
                if h[0] == "BUILD_PASTURE": champ_pastures_built[day] += 1
                elif h[0] == "PLACE" and len(h) > 1:
                    if h[1] == "COW": champ_cows_placed[day] += 1
                    elif h[1] == "SHEEP": champ_sheep_placed[day] += 1
                    
    if hour == 23 and day in (4, 5, 8, 11, 28, 29):
        tiles = f0["tiles"]
        cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
        sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
        pastures = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE")
        money = f0["money"]
        unlocked = len(f0["unlocked_quadrants"])
        champ_milestones[day] = {
            "cows": cows, "sheep": sheep, "pastures": pastures,
            "money": money, "unlocked": unlocked,
            "feed": champ_actions_cum["FEED"],
            "care": champ_actions_cum["CARE"],
            "collect_fert": champ_actions_cum["COLLECT_FERTILIZER"],
            "pass": champ_actions_cum["PASS"],
        }

# 2. PROFILE RC4.2 (SEAT 0 on same seed and opponent)
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

rc42_milestones = {}
rc42_actions_cum = Counter()
rc42_cows_placed = Counter()
rc42_sheep_placed = Counter()
rc42_pastures_built = Counter()

# Tracking animal servicing in RC4.2: opportunities vs completions
rc42_animal_days_total = 0
rc42_animal_days_fed = 0
rc42_animal_days_cared = 0

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[0].observation
    day = obs["day"]
    hour = obs["hour"]
    
    act = rc42.agent(obs)
    if isinstance(act, dict):
        for h in act.get("hands", []):
            if h:
                rc42_actions_cum[h[0]] += 1
                if h[0] == "BUILD_PASTURE": rc42_pastures_built[day] += 1
                elif h[0] == "PLACE" and len(h) > 1:
                    if h[1] == "COW": rc42_cows_placed[day] += 1
                    elif h[1] == "SHEEP": rc42_sheep_placed[day] += 1
                    
    env.step([act, opp_actions[s]])
    
    f0 = env.state[0].observation["farms"][0]
    if hour == 16: # Mid-afternoon servicing check
        for r in f0.get("tiles", []):
            for t in r:
                if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"):
                    rc42_animal_days_total += 1
                    if t.get("fed_today", False): rc42_animal_days_fed += 1
                    if t.get("cared_today", False): rc42_animal_days_cared += 1
                    
    if hour == 23 and day in (4, 5, 8, 11, 28, 29):
        tiles = f0["tiles"]
        cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
        sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
        pastures = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("kind") == "PASTURE")
        money = f0["money"]
        unlocked = len(f0["unlocked_quadrants"])
        rc42_milestones[day] = {
            "cows": cows, "sheep": sheep, "pastures": pastures,
            "money": money, "unlocked": unlocked,
            "feed": rc42_actions_cum["FEED"],
            "care": rc42_actions_cum["CARE"],
            "collect_fert": rc42_actions_cum["COLLECT_FERTILIZER"],
            "pass": rc42_actions_cum["PASS"],
        }

print("=" * 110)
print("RC5-0.5 CAUSAL DECOMPOSITION: CHAMPION ($146K) vs RC4.2 ($20K) ON SEED 91697084")
print("=" * 110)
print(f"{'DAY':<4} | {'METRIC':<18} | {'CHAMPION ($146K)':<25} | {'RC4.2 ($20K)':<25} | {'GAP / DELTA':<20}")
print("-" * 110)

for d in (4, 5, 8, 11, 28):
    cm = champ_milestones.get(d, {})
    rm = rc42_milestones.get(d, {})
    
    print(f"D{d:02d}  | Cash on Hand       | ${cm.get('money', 0):>10,.0f}              | ${rm.get('money', 0):>10,.0f}              | ${cm.get('money', 0)-rm.get('money', 0):>+10,.0f}")
    print(f"     | Pastures Built     | {cm.get('pastures', 0):>10} pastures         | {rm.get('pastures', 0):>10} pastures         | {cm.get('pastures', 0)-rm.get('pastures', 0):>+10} pastures")
    print(f"     | Total Living Herd  | {cm.get('cows', 0)+cm.get('sheep', 0):>6} ({cm.get('cows', 0)}C / {cm.get('sheep', 0)}S)     | {rm.get('cows', 0)+rm.get('sheep', 0):>6} ({rm.get('cows', 0)}C / {rm.get('sheep', 0)}S)     | {cm.get('cows', 0)+cm.get('sheep', 0)-(rm.get('cows', 0)+rm.get('sheep', 0)):>+10} animals")
    print(f"     | Cum. FEED Actions  | {cm.get('feed', 0):>10} feeds            | {rm.get('feed', 0):>10} feeds            | {cm.get('feed', 0)-rm.get('feed', 0):>+10} feeds")
    print(f"     | Cum. CARE Actions  | {cm.get('care', 0):>10} cares            | {rm.get('care', 0):>10} cares            | {cm.get('care', 0)-rm.get('care', 0):>+10} cares")
    print(f"     | Cum. COLLECT FERT  | {cm.get('collect_fert', 0):>10} fert             | {rm.get('collect_fert', 0):>10} fert             | {cm.get('collect_fert', 0)-rm.get('collect_fert', 0):>+10} fert")
    print(f"     | Cum. PASS Actions  | {cm.get('pass', 0):>10} passes           | {rm.get('pass', 0):>10} passes           | {cm.get('pass', 0)-rm.get('pass', 0):>+10} passes")
    print("-" * 110)

print("=" * 110)
