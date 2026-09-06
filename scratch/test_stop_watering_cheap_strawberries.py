import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

# Load Soumi Ghosh replay
with open(r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json") as f:
    rep = json.load(f)
steps = rep["steps"]
opp_actions = [frame[0].get("action") for frame in steps[1:]]

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": rep["info"]["seed"]})
env.reset()

suppressed_watering_actions = 0

for step in range(len(steps) - 1):
    if env.done: break
    obs = env.state[1].observation
    p_straw = float(obs.market.prices.get("STRAWBERRY", 120))
    
    act1 = rc2_mod.agent(obs)
    
    # If price < 50, filter out WATER actions on strawberry tiles
    if p_straw < 50.0 and isinstance(act1, dict):
        farm = obs.farms[1]
        filtered_hands = []
        for h_act in act1.get("hands", []):
            if h_act and len(h_act) >= 3 and h_act[0] == "WATER":
                r, c = h_act[1], h_act[2]
                tile = farm.tiles[r][c]
                if isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY":
                    suppressed_watering_actions += 1
                    continue # Do not waste labor watering $18 strawberries!
            filtered_hands.append(h_act)
        act1["hands"] = filtered_hands
        
    env.step([opp_actions[step], act1])

final_score = env.state[1].observation.farms[1].money
print(f"Counterfactual Result (Suppress Strawberry Watering when P < $50):")
print(f"Suppressed Watering Actions: {suppressed_watering_actions}")
print(f"Final Score:                 ${final_score:,.0f} (Baseline: $21,856)")
print(f"Score Delta:                 ${final_score - 21856:+,.0f}")
