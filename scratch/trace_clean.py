import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_v4_1_clean as clean

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1362511072})
env.reset()

for s in range(30):
    obs = env.state[0].observation
    act = clean.agent(obs)
    if s % 6 == 0:
        farm = obs["farms"][0]
        print(f"Step {s:02d} | Day {s//24} H {s%24:02d} | Money: ${farm['money']} | Farmer: {act.get('farmer')} | Hands: {len(act.get('hands', []))} | Market: {act.get('market')}")
    env.step([act, {"farmer": ["PASS"], "hands": [], "market": []}])
