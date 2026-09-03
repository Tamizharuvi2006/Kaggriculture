import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments
import submission_challenger_exp208_clean as challenger

seed = 1624303674

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(75):
    obs1 = env.state[1].observation
    act1 = challenger.agent(obs1)
    
    farm1 = obs1.get("farms", [])[1]
    priv1 = obs1.get("private", {})
    shed1 = priv1.get("shed", {})
    money = farm1.get("money", 0)
    
    print(f"Step {s:2d}: Cash ${money:7.1f} | Market: {act1.get('market')} | Shed: {shed1}")
    
    actions = [{"farmer": ["PASS"], "hands": [], "market": []}, act1]
    env.step(actions)
