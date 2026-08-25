"""
Observability and Schema Audit for Kaggle Environments v1.32.6
Inspects exact observation dictionaries for Player 0 and Player 1
"""
import kaggle_environments
import pprint
import json

env = kaggle_environments.make('kaggriculture', configuration={'episodeSteps': 720, 'seed': 42})
env.reset()

obs0 = env.state[0]['observation']
obs1 = env.state[1]['observation']

print("=== KEYS IN PLAYER 0 OBS ===")
print(list(obs0.keys()))

print("\n=== PRIVATE IN OBS0 ===")
print(obs0.get('private'))

print("\n=== FARMS IN OBS0 ===")
print(f"Number of farms: {len(obs0.get('farms', []))}")
for i, farm in enumerate(obs0.get('farms', [])):
    print(f"\n--- Farm [{i}] ---")
    for k, v in farm.items():
        if k == 'tiles':
            print(f"  tiles: {len(v)} tiles (sample: {v[:2] if isinstance(v, list) else list(v.items())[:2]})")
        else:
            print(f"  {k}: {v}")

# Step 48 turns to accumulate some crop and animal production
for s in range(48):
    env.step([{'farmer': ['PASS']}, {'farmer': ['PASS']}])

obs48 = env.state[0]['observation']
print("\n=== AT STEP 48 ===")
for i, farm in enumerate(obs48.get('farms', [])):
    print(f"\n--- Farm [{i}] at Step 48 ---")
    for k, v in farm.items():
        if k != 'tiles':
            print(f"  {k}: {v}")
print("Private shed at Step 48:", obs48.get('private'))
