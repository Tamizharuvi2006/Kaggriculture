import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

print("=========================================================================================")
print("     STEP-BY-STEP COMPARISON: ARAO (P0) VS HERO (P1) ON DAY 0 (STEPS 0 TO 23)            ")
print("=========================================================================================")

for s in range(1, 25): # steps 1 to 24 in replay correspond to game steps 0 to 23
    act0 = steps[s][0].get("action", {})
    act1 = steps[s][1].get("action", {})
    
    f0 = act0.get("farmer", ["PASS"])
    f1 = act1.get("farmer", ["PASS"])
    
    h0 = act0.get("hands", [])
    h1 = act1.get("hands", [])
    
    m0 = act0.get("market", [])
    m1 = act1.get("market", [])
    
    print(f"Step {s-1:2d}:")
    print(f"  ARAO (P0): Farmer={f0} | Hands={len(h0)} {h0[:2]} | Mkt={m0}")
    print(f"  HERO (P1): Farmer={f1} | Hands={len(h1)} {h1[:2]} | Mkt={m1}")
    print("-" * 90)
