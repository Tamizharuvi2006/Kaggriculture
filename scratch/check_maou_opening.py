import json

with open(r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", "r", encoding="utf-8") as f:
    rep = json.load(f)

steps = rep["steps"]
for s in range(120, 288):
    obs = steps[s][0]["observation"]
    act = steps[s][0].get("action", {})
    m = act.get("market", [])
    if m:
        # Only print non-routine single wheat trades to keep output concise
        non_routine = [x for x in m if x[0] in ("BUY_LAND", "BUY_ANIMAL", "HIRE") or (x[0] == "BUY_SEED" and x[1] in ("STRAWBERRY", "MELON"))]
        if non_routine:
            print(f"Step {s:03d} (D{obs['day']:02d}H{obs['hour']:02d}, money=${obs['farms'][0]['money']}): {non_routine}")

