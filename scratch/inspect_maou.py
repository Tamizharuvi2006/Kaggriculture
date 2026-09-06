import json

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]

# In episode 91697084, who was Maou? Seat 0 or Seat 1?
name_0 = rep["info"]["TeamNames"][0]
name_1 = rep["info"]["TeamNames"][1]
print(f"Seat 0: {name_0} | Seat 1: {name_1}")

seat = 0 if "maou" in name_0.lower() else (1 if "maou" in name_1.lower() else 0)
print(f"Target seat: {seat}")

for s in range(0, len(steps), 24):
    step = steps[s]
    obs = step[seat]["observation"]
    day = obs["day"]
    farm = obs["farms"][seat]
    shed = obs["private"]["shed"]
    tiles = farm["tiles"]
    cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    chickens = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "CHICKEN")
    
    crops = {}
    for r in tiles:
        for t in r:
            if isinstance(t, dict) and t.get("crop"):
                c = t["crop"]
                crops[c] = crops.get(c, 0) + 1
    
    crop_str = ", ".join(f"{k}:{v}" for k, v in crops.items())
    print(f"Day {day:02d}: Money=${farm['money']:>7,.0f} | Cows={cows}, Sheep={sheep}, Chk={chickens} | Crops: [{crop_str}]")
