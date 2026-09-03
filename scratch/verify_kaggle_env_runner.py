import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208_clean as challenger

print("Testing kaggle_environments.make('kaggriculture').run(...)")
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
res = env.run([challenger.agent, challenger.agent])

r0 = res[-1][0]["reward"]
r1 = res[-1][1]["reward"]
st0 = res[-1][0]["status"]
st1 = res[-1][1]["status"]

print(f"Self-play run finished cleanly:")
print(f"  P0: Status={st0}, Reward=${r0:,.0f}")
print(f"  P1: Status={st1}, Reward=${r1:,.0f}")
print(f"  Error P0: {res[-1][0].get('info')}")
print(f"  Error P1: {res[-1][1].get('info')}")
