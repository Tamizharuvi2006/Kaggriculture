import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()

print("INITIAL:")
obs1 = env.state[1].observation
print("  obs1.get('step'):", obs1.get("step"))
print("  obs1.get('day'):", obs1.get("day"))
print("  obs1.get('hour'):", obs1.get("hour"))

env.step([{"farmer": ["PASS"], "hands": [], "market": []}, {"farmer": ["PASS"], "hands": [], "market": []}])

print("AFTER STEP 1:")
obs1 = env.state[1].observation
print("  obs1.get('step'):", obs1.get("step"))
print("  obs1.get('day'):", obs1.get("day"))
print("  obs1.get('hour'):", obs1.get("hour"))
