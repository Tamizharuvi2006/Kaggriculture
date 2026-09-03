import json
import os

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"

print(f"Loading {replay_path} ({os.path.getsize(replay_path):,} bytes)...")
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

info = replay.get("info", {})
print("Seed:", info.get("seed"))
agents = info.get("Agents", [])
team_names = info.get("TeamNames", [])
print(f"Player 0: {team_names[0] if team_names else 'N/A'}")
print(f"Player 1: {team_names[1] if team_names else 'N/A'}")
rewards = replay.get("rewards", [])
print(f"Rewards: P0={rewards[0]} vs P1={rewards[1]}")

steps = replay.get("steps", [])
print(f"Total steps in replay: {len(steps)}")

# Dissect trajectories every day (24 steps) and key moments
print("\n" + "=" * 120)
print(f"{'Day':>3} | {'Step':>4} | {'P0 (arao) Cash':>14} | {'P0 Lands':>8} | {'P0 Hands':>8} | {'P0 Shed/Stock':>25} || {'P1 (Hero) Cash':>14} | {'P1 Lands':>8} | {'P1 Hands':>8} | {'P1 Shed/Stock':>25}")
print("=" * 120)

for s in range(0, len(steps), 24):
    frame = steps[s]
    obs0 = frame[0].get("observation", {})
    obs1 = frame[1].get("observation", {})
    
    farm0 = (obs0.get("farms") or [{}])[0]
    farm1 = (obs1.get("farms") or [{}, {}])[1]
    
    priv0 = obs0.get("private", {})
    priv1 = obs1.get("private", {})
    
    shed0 = priv0.get("shed", {})
    shed1 = priv1.get("shed", {})
    
    c0 = farm0.get("money", 0)
    c1 = farm1.get("money", 0)
    
    l0 = len(farm0.get("unlocked_quadrants", []))
    l1 = len(farm1.get("unlocked_quadrants", []))
    
    h0 = len(farm0.get("hands", []))
    h1 = len(farm1.get("hands", []))
    
    stock0 = f"M:{shed0.get('MILK',0)} W:{shed0.get('WOOL',0)} S:{shed0.get('STRAWBERRY',0)} C:{shed0.get('COW',0)}"
    stock1 = f"M:{shed1.get('MILK',0)} W:{shed1.get('WOOL',0)} S:{shed1.get('STRAWBERRY',0)} C:{shed1.get('COW',0)}"
    
    day = s // 24
    print(f"{day:3d} | {s:4d} | ${c0:13.1f} | {l0:8d} | {h0:8d} | {stock0:>25} || ${c1:13.1f} | {l1:8d} | {h1:8d} | {stock1:>25}")

print("\n" + "=" * 120)
print("     ARAO (P0) CRITICAL ACTIONS TIMELINE (BUY_LAND, HIRE, ANIMALS, MAJOR SELLS)        ")
print("=" * 120)

for s, frame in enumerate(steps):
    act0 = frame[0].get("action", {})
    market0 = act0.get("market", [])
    farmer0 = act0.get("farmer", [])
    
    notable = []
    for m in market0:
        if isinstance(m, list) and len(m) > 0:
            if m[0] in ("BUY_LAND", "HIRE", "BUY_ANIMAL") or (m[0] == "SELL" and len(m) > 2 and m[2] >= 3):
                notable.append(m)
                
    if notable or (len(farmer0) > 0 and farmer0[0] in ("BUILD_PASTURE", "BUILD_COOP")):
        day = s // 24
        hour = s % 24
        print(f"Step {s:3d} (Day {day:2d}, h {hour:2d}): Market={notable} | Farmer={farmer0}")
        if s > 250:
            # summarize after day 10
            pass
