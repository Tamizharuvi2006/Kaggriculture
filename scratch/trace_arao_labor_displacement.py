import json, kaggle_environments, sys
sys.path.insert(0, r"D:\kaggriculture")
from collections import Counter
import submission_rc4_2_hybrid as rc42
import submission_rc5_a_early_pasture as rc5a

path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(path) as f: rep = json.load(f)
steps = rep["steps"]
opp_actions = [steps[s][0].get("action") for s in range(1, len(steps))]

def trace_opening_actions(agent_mod, name):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    events = []
    melon_harvest_times = []
    straw_plant_times = []
    pasture_build_times = []
    cash_by_day = {}
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[1].observation
        day = obs["day"]
        hour = obs["hour"]
        
        act = agent_mod.agent(obs)
        if isinstance(act, dict):
            for h in act.get("hands", []):
                if h:
                    if h[0] == "BUILD_PASTURE":
                        pasture_build_times.append((day, hour))
                    elif h[0] == "PLANT" and len(h) > 1 and h[1] == "STRAWBERRY":
                        straw_plant_times.append((day, hour))
                    elif h[0] == "HARVEST":
                        # Check tile being harvested
                        pass
        env.step([opp_actions[s], act])
        
        f1 = env.state[1].observation["farms"][1]
        if hour == 23 and day <= 12:
            cash_by_day[day] = f1["money"]
            
    print(f"\n--- {name} EVENT TRACE ---")
    print(f"Pasture BUILD Actions (Days 0-5): {pasture_build_times[:10]}")
    print(f"Strawberry PLANT Actions (Days 0-10): {len(straw_plant_times)} total planted")
    print(f"First 5 Strawberry Plantings: {straw_plant_times[:5]}")
    print(f"Cash on Hand Days 0-6: {[round(cash_by_day.get(d, 0)) for d in range(7)]}")
    
    # End state crops
    f1 = env.state[1].observation["farms"][1]
    tiles = f1["tiles"]
    straws = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
    melons = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "MELON")
    cows = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "COW")
    sheep = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("animal") == "SHEEP")
    print(f"Day 30 Final State: Final Money=${f1['money']:,.0f} | Strawberries in soil={straws} | Melons={melons} | Cows={cows} | Sheep={sheep}")

print("=" * 80)
print("FORENSIC TRACE OF LABOR DISPLACEMENT: ARAO PASSIVE MATCH")
print("=" * 80)
trace_opening_actions(rc42, "RC4.2 (Control)")
trace_opening_actions(rc5a, "RC5-A (Early Pasture)")
print("=" * 80)
