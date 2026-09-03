import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_rc1_ev_dispatcher as rc1
import time

t0 = time.time()
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
res = env.run([rc1.agent, rc1.agent])
elapsed = time.time() - t0

p0_reward = res[-1][0]["reward"]
p1_reward = res[-1][1]["reward"]
p0_status = res[-1][0]["status"]
p1_status = res[-1][1]["status"]

print(f"RC1 Self-Play Validation Completed in {elapsed:.2f}s (~{elapsed*1000/720/2:.2f} ms/agent-step)!")
print(f"Player 0 Reward: ${p0_reward:,.0f} (Status: {p0_status})")
print(f"Player 1 Reward: ${p1_reward:,.0f} (Status: {p1_status})")
assert p0_status == "DONE" and p1_status == "DONE"
print("SUCCESS: 100% Kaggle Environment Compliant!")
