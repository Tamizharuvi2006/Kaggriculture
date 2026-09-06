import os, sys, json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
hero_seat = 0

with open(replay_path, "r", encoding="utf-8") as f:
    rep = json.load(f)
steps = rep["steps"]
opp_seat = 1 - hero_seat
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

# 1. Run RC12
sys.path.insert(0, r"D:\kaggriculture")
import submission_rc12

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

rc12_daily = {}

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[hero_seat].observation
    day = obs["day"]
    hour = obs["hour"]
    act = submission_rc12.agent(obs)
    
    if day not in rc12_daily:
        rc12_daily[day] = {
            "money": 0,
            "animals": {"COW": 0, "SHEEP": 0},
            "crops": {},
            "workers": 0,
            "buys": [],
            "sells": [],
            "wheat_shed": 0,
            "actions_count": {"FEED": 0, "CARE": 0, "WATER": 0, "HARVEST": 0, "PLANT": 0, "PICKUP": 0, "DROP": 0, "FERTILIZE": 0}
        }
    
    # Track unit actions
    for unit_acts in [act.get("farmer", [])] + act.get("hands", []):
        if not unit_acts: continue
        atype = unit_acts[0]
        if atype in rc12_daily[day]["actions_count"]:
            rc12_daily[day]["actions_count"][atype] += 1
            
    # Track market actions
    for m in act.get("market", []):
        if not m: continue
        if m[0] in ("BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT"):
            rc12_daily[day]["buys"].append((m[0], m[1], m[2] if len(m) > 2 else 1))
        elif m[0] == "SELL":
            rc12_daily[day]["sells"].append((m[1], m[2] if len(m) > 2 else 1))

    if hero_seat == 0:
        env.step([act, opp_actions[s]])
    else:
        env.step([opp_actions[s], act])

    farm = env.state[hero_seat].observation["farms"][hero_seat]
    rc12_daily[day]["money"] = farm["money"]
    rc12_daily[day]["workers"] = len(farm.get("workers", []))
    tiles = farm.get("tiles", [])
    rc12_daily[day]["animals"]["COW"] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    rc12_daily[day]["animals"]["SHEEP"] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    rc12_daily[day]["crops"] = {}
    for r in tiles:
        for t in r:
            if isinstance(t, dict) and t.get("crop"):
                c = t["crop"]
                rc12_daily[day]["crops"][c] = rc12_daily[day]["crops"].get(c, 0) + 1

# Extract Maou daily from replay
maou_daily = {}
for s in range(1, len(steps)):
    obs = steps[s][hero_seat]["observation"]
    act = steps[s][hero_seat].get("action") or {}
    day = obs.get("day", 0)
    farm = obs["farms"][hero_seat]
    if day not in maou_daily:
        maou_daily[day] = {
            "money": 0,
            "animals": {"COW": 0, "SHEEP": 0},
            "crops": {},
            "workers": 0,
            "actions_count": {"FEED": 0, "CARE": 0, "WATER": 0, "HARVEST": 0, "PLANT": 0, "PICKUP": 0, "DROP": 0, "FERTILIZE": 0}
        }
    maou_daily[day]["money"] = farm.get("money", 0)
    maou_daily[day]["workers"] = len(farm.get("workers", []))
    tiles = farm.get("tiles", [])
    maou_daily[day]["animals"]["COW"] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    maou_daily[day]["animals"]["SHEEP"] = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    maou_daily[day]["crops"] = {}
    for r in tiles:
        for t in r:
            if isinstance(t, dict) and t.get("crop"):
                c = t["crop"]
                maou_daily[day]["crops"][c] = maou_daily[day]["crops"].get(c, 0) + 1
    for unit_acts in [act.get("farmer", [])] + act.get("hands", []):
        if not unit_acts: continue
        atype = unit_acts[0]
        if atype in maou_daily[day]["actions_count"]:
            maou_daily[day]["actions_count"][atype] += 1

print("=" * 120)
print(f"{'DAY':<4} | {'MAOU $':>8} | {'RC12 $':>8} | {'MAOU COWS/SHP':<14} | {'RC12 COWS/SHP':<14} | {'MAOU CROPS':<25} | {'RC12 CROPS':<25}")
print("=" * 120)
for d in sorted(set(maou_daily.keys()).intersection(rc12_daily.keys())):
    m = maou_daily[d]
    r = rc12_daily[d]
    m_anim = f"{m['animals']['COW']}c / {m['animals']['SHEEP']}s"
    r_anim = f"{r['animals']['COW']}c / {r['animals']['SHEEP']}s"
    m_crops = ", ".join(f"{k}:{v}" for k, v in m["crops"].items())
    r_crops = ", ".join(f"{k}:{v}" for k, v in r["crops"].items())
    print(f"D{d:<3} | ${m['money']:>7,.0f} | ${r['money']:>7,.0f} | {m_anim:<14} | {r_anim:<14} | {m_crops:<25} | {r_crops:<25}")

print("\n" + "=" * 120)
print(f"{'DAY':<4} | {'MAOU ACTIONS (HARV / CARE / FEED / WATER / FERT)':<55} | {'RC12 ACTIONS (HARV / CARE / FEED / WATER / FERT)':<55}")
print("=" * 120)
for d in [0, 1, 3, 5, 8, 10, 12, 15, 18, 22, 25, 28]:
    if d in maou_daily and d in rc12_daily:
        ma = maou_daily[d]["actions_count"]
        ra = rc12_daily[d]["actions_count"]
        m_str = f"H:{ma['HARVEST']} C:{ma['CARE']} F:{ma['FEED']} W:{ma['WATER']} FERT:{ma['FERTILIZE']}"
        r_str = f"H:{ra['HARVEST']} C:{ra['CARE']} F:{ra['FEED']} W:{ra['WATER']} FERT:{ra['FERTILIZE']}"
        print(f"D{d:<3} | {m_str:<55} | {r_str:<55}")
