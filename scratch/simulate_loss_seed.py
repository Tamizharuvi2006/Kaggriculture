import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
from submission_rc2_terminal_horizon import agent as rc2_agent

seed = 334330253 # The seed from Episode 105105439 (zZx Hee: $90,305 vs Our RC2: $38,075)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

print("Simulating live loss seed 334330253 under RC2 self-play...")
for step in range(720):
    if env.done: break
    act0 = rc2_agent(env.state[0].observation)
    act1 = rc2_agent(env.state[1].observation)
    env.step([act0, act1])

obs = env.state[0].observation
f0 = obs.farms[0]
f1 = obs.farms[1]
print(f"Final Money: P0: ${f0.money:,.0f} | P1: ${f1.money:,.0f}")
print(f"End state: Day {obs.day} Hour {obs.hour}")
print("P0 unlocked quadrants:", f0.unlocked_quadrants)
print("P1 unlocked quadrants:", f1.unlocked_quadrants)
print("Market prices at end:", obs.market.prices)
print("Market inventory at end:", obs.market.inventory)
