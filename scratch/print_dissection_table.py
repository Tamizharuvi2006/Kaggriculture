import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

print("=" * 135)
print(f"{'Day':>3} | {'P0 (arao) Cash':>14} | {'P0 Lands':>8} | {'P0 Hands':>8} | {'P0 Animals':>15} || {'P1 (Hero) Cash':>14} | {'P1 Lands':>8} | {'P1 Hands':>8} | {'P1 Animals':>15}")
print("=" * 135)

for s in range(0, len(steps), 24):
    frame = steps[s]
    obs0 = frame[0].get("observation", {})
    obs1 = frame[1].get("observation", {})
    farm0 = (obs0.get("farms") or [{}])[0]
    farm1 = (obs1.get("farms") or [{}, {}])[1]
    
    # Count animals
    c0, s0, g0 = 0, 0, 0
    for row in farm0.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict):
                a = tile.get("animal")
                if a == "COW": c0 += 1
                elif a == "SHEEP": s0 += 1
                elif a == "GOOSE": g0 += 1
                
    c1, s1, g1 = 0, 0, 0
    for row in farm1.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict):
                a = tile.get("animal")
                if a == "COW": c1 += 1
                elif a == "SHEEP": s1 += 1
                elif a == "GOOSE": g1 += 1
                
    cash0 = farm0.get("money", 0)
    cash1 = farm1.get("money", 0)
    l0 = len(farm0.get("unlocked_quadrants", []))
    l1 = len(farm1.get("unlocked_quadrants", []))
    h0 = len(farm0.get("hands", []))
    h1 = len(farm1.get("hands", []))
    
    day = s // 24
    print(f"{day:3d} | ${cash0:13.1f} | {l0:8d} | {h0:8d} | Cows:{c0:2d} Sheep:{s0:2d} || ${cash1:13.1f} | {l1:8d} | {h1:8d} | Cows:{c1:2d} Sheep:{s1:2d}")
