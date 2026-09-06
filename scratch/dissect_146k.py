import json

replay_path = "D:/kaggriculture/reports/step5b/old_loss_gauntlet/raw_replays/91697084/episode-91697084-replay.json"
with open(replay_path, "r") as f:
    rep = json.load(f)

steps = rep["steps"]
print("Winner final money:", steps[-1][0]["observation"]["farms"][0]["money"])

# Track sales by item
sales = {}
animal_buys = []
hires = []
seeds = {}

for s in range(len(steps)):
    act = steps[s][0].get("action")
    if not act: continue
    obs = steps[s][0].get("observation")
    prices = obs["market"]["prices"] if obs else {}
    for o in act.get("market", []):
        if not o: continue
        op = o[0]
        if op == "SELL":
            item, qty = o[1], o[2]
            p = prices.get(item, 0)
            sales[item] = sales.get(item, 0) + qty * p * 0.95
        elif op == "BUY_ANIMAL":
            animal_buys.append((obs["day"], o[1], o[2]))
        elif op == "HIRE":
            hires.append(obs["day"])
        elif op == "BUY_SEED":
            seeds[o[1]] = seeds.get(o[1], 0) + o[2]

print("\n--- Seat 0 Sales Breakdown (Winner: $146,972) ---")
for item, val in sorted(sales.items(), key=lambda x: -x[1]):
    print(f"  {item:<12}: ${val:>8,.0f}")

print("\nAnimal Buys:", animal_buys)
print("Total Hires:", len(hires))
print("Seeds Bought:", seeds)
