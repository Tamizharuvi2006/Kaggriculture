import json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

arao_actions = [frame[0].get("action") for frame in steps[1:]]
hero_recorded_actions = [frame[1].get("action") for frame in steps[1:]]

def run_test(wool_floor, milk_floor, straw_floor):
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    for s in range(len(arao_actions)):
        if env.done:
            break
            
        act0 = arao_actions[s]
        act1 = json.loads(json.dumps(hero_recorded_actions[s])) # copy
        
        # Check current market prices
        obs1 = env.state[1].observation
        prices = obs1.get("market", {}).get("prices", {})
        p_wool = float(prices.get("WOOL", 200))
        p_milk = float(prices.get("MILK", 160))
        p_straw = float(prices.get("STRAWBERRY", 120))
        
        # Filter fire-sale market orders if not end of game (s < 690)
        if s < 690 and "market" in act1:
            clean_mkt = []
            for order in act1.get("market", []):
                if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL":
                    prod = order[1]
                    if prod == "WOOL" and p_wool < wool_floor:
                        continue
                    if prod == "MILK" and p_milk < milk_floor:
                        continue
                    if prod == "STRAWBERRY" and p_straw < straw_floor:
                        continue
                clean_mkt.append(order)
            act1["market"] = clean_mkt
            
        env.step([act0, act1])
        
    rew0 = env.state[0].reward
    rew1 = env.state[1].reward
    return rew0, rew1

print("=========================================================================================")
print("     PARAMETRIC TEST: PRICE REALIZATION FLOORS VS EXACT ARAO REPLAY                      ")
print("=========================================================================================")
print(f"Base Live Result: arao = $55,146 | Hero = $40,642 (Loss: -14,504)")

for wf in [1, 20, 40, 60]:
    for mf in [1, 20, 40]:
        for sf in [1, 30, 50]:
            r0, r1 = run_test(wf, mf, sf)
            margin = r1 - r0
            if margin > -14504 or r1 > 40642:
                print(f"Floors (Wool>{wf}, Milk>{mf}, Straw>{sf}): arao=${r0:,.0f} | Hero=${r1:,.0f} | Margin={margin:+,.0f}")
