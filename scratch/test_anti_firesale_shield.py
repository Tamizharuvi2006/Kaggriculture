import json
import kaggle_environments

# Load arao's exact actions from the replay
replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

arao_actions = [frame[0].get("action") for frame in steps]

import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

# Let's test a modified agent that filters out fire-sales:
# Never sell WOOL < 60, MILK < 45, STRAWBERRY < 45, MELON < 80 unless step >= 690
def agent_shielded(obs):
    act = challenger.agent(obs)
    if not isinstance(act, dict):
        return act
        
    step = int(obs.get("step") if obs.get("step") is not None else int(obs.get("day", 0))*24 + int(obs.get("hour", 0)))
    
    if step >= 690:
        return act # Final liquidation allows everything
        
    prices = obs.get("market", {}).get("prices", {})
    p_wool = float(prices.get("WOOL", 200))
    p_milk = float(prices.get("MILK", 160))
    p_straw = float(prices.get("STRAWBERRY", 120))
    p_melon = float(prices.get("MELON", 250))
    
    # Filter fire-sales from market orders
    clean_market = []
    for order in act.get("market", []):
        if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL":
            prod = order[1]
            if prod == "WOOL" and p_wool < 60.0:
                continue
            if prod == "MILK" and p_milk < 45.0:
                continue
            if prod == "STRAWBERRY" and p_straw < 45.0:
                continue
            if prod == "MELON" and p_melon < 80.0:
                continue
        clean_market.append(order)
        
    act["market"] = clean_market
    return act

# Run simulation
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done:
        break
    obs1 = env.state[1].observation
    act1 = agent_shielded(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])

reward_arao = env.state[0].reward
reward_hero = env.state[1].reward

print("=========================================================================================")
print(f"     COUNTERFACTUAL TEST WITH ANTI-FIRE-SALE SHIELD ON EPISODE 104379472                ")
print("=========================================================================================")
print(f"Original Live Match: arao = $55,146 | Hero = $40,642 (Loss by -$14,504)")
print(f"With Shielded Agent: arao = ${reward_arao:,.0f} | Hero = ${reward_hero:,.0f} (Margin: {reward_hero - reward_arao:+,.0f})")
