import json

replay_file = r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json"
with open(replay_file) as f: rep = json.load(f)

steps = rep["steps"]
ricardo_seat = 1

# Analyze Ricardo's key actions and milestones
hires = 0
land_unlocks = []
animals_bought = []
seeds_bought = {}
products_sold = {}

for s, frame in enumerate(steps[1:]):
    act = frame[ricardo_seat].get("action", {}) or {}
    mkt = act.get("market", []) or []
    obs = frame[ricardo_seat].get("observation", {}) or {}
    day = s // 24
    hour = s % 24
    
    for order in mkt:
        if not isinstance(order, list) or len(order) == 0: continue
        cmd = order[0]
        if cmd == "HIRE":
            hires += 1
        elif cmd == "BUY_LAND":
            land_unlocks.append((day, hour))
        elif cmd == "BUY_ANIMAL":
            animals_bought.append((day, hour, order[1], order[2] if len(order) > 2 else 1))
        elif cmd == "BUY_SEED":
            seeds_bought[order[1]] = seeds_bought.get(order[1], 0) + (order[2] if len(order) > 2 else 1)
        elif cmd == "SELL":
            products_sold[order[1]] = products_sold.get(order[1], 0) + (order[2] if len(order) > 2 else 1)

print("=== RICARDO LOPEZ AUDIT (Episode 104475527) ===")
print("Total Hires:", hires)
print("Land Unlocks:", land_unlocks)
print("Animals Bought:", animals_bought)
print("Seeds Bought:", seeds_bought)
print("Products Sold:", products_sold)
