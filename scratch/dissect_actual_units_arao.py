import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

# Track money change for arao and Hero from step 480 (Day 20) to 719 (Day 30)
c0_start = steps[480][0]["observation"]["farms"][0]["money"]
c0_end = steps[-1][0]["observation"]["farms"][0]["money"]

c1_start = steps[480][1]["observation"]["farms"][1]["money"]
c1_end = steps[-1][1]["observation"]["farms"][1]["money"]

print(f"ARAO (P0): Day 20 = ${c0_start:,.0f} -> Day 30 = ${c0_end:,.0f} (Gain: +${c0_end - c0_start:,.0f})")
print(f"HERO (P1): Day 20 = ${c1_start:,.0f} -> Day 30 = ${c1_end:,.0f} (Gain: +${c1_end - c1_start:,.0f})")

# Look at expenses (what did they buy in Days 20 to 30?)
for name, p_idx in [("ARAO", 0), ("HERO", 1)]:
    spent = 0.0
    hires = 0
    seeds = 0
    animals = 0
    feed = 0
    for s in range(481, len(steps)):
        act = steps[s][p_idx].get("action", {})
        for m in act.get("market", []):
            if isinstance(m, list) and len(m) > 0:
                if m[0] == "HIRE": hires += 1
                elif m[0] == "BUY_SEED": seeds += int(m[2]) if len(m) > 2 else 1
                elif m[0] == "BUY_ANIMAL": animals += int(m[2]) if len(m) > 2 else 1
                elif m[0] == "BUY_PRODUCT" and len(m) > 1 and m[1] == "WHEAT": feed += int(m[2]) if len(m) > 2 else 1
    print(f"{name} Expenses Days 20-30: Hires={hires}, Seeds={seeds}, Animals={animals}, Feed={feed}")
