import json

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])

print("=========================================================================================")
print("     HERO (P1) VS ARAO (P0) ENDGAME AUTOPSY (DAYS 23 TO 29, STEPS 552 TO 720)            ")
print("=========================================================================================")

for s in range(552, len(steps), 12): # Every 12 steps (half day)
    frame = steps[s]
    obs0 = frame[0].get("observation", {})
    obs1 = frame[1].get("observation", {})
    farm0 = (obs0.get("farms") or [{}])[0]
    farm1 = (obs1.get("farms") or [{}, {}])[1]
    
    priv0 = obs0.get("private", {})
    priv1 = obs1.get("private", {})
    shed0 = priv0.get("shed", {})
    shed1 = priv1.get("shed", {})
    
    prices = obs0.get("market", {}).get("prices", {})
    
    day = s // 24
    hour = s % 24
    
    print(f"Step {s:3d} (D{day:2d} h{hour:2d}):")
    print(f"  P0 (arao): Cash ${farm0.get('money',0):,.0f} | Shed: {shed0}")
    print(f"  P1 (Hero): Cash ${farm1.get('money',0):,.0f} | Shed: {shed1}")
    print(f"  Prices: Milk ${prices.get('MILK',0)}, Wool ${prices.get('WOOL',0)}, Straw ${prices.get('STRAWBERRY',0)}, Fert ${prices.get('FERTILIZER',0)}")
    
    act0 = frame[0].get("action", {})
    act1 = frame[1].get("action", {})
    print(f"  P0 Market orders: {act0.get('market', [])}")
    print(f"  P1 Market orders: {act1.get('market', [])}")
    print("-" * 100)
