"""
Causal & Mechanical Audit for EXP-0123 (Town Shop Wheat Feed Preemption)
Inspects kaggle_environments v1.32.6 market dynamics:
- Tests order execution for BUY_PRODUCT WHEAT
- Measures market inventory reduction and price elasticity
- Checks replenishment rates across steps 0..720
"""
import kaggle_environments
import json
import pprint

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()

print("=== INITIAL MARKET STATE ===")
obs0 = env.state[0]["observation"]
print("Market Inventory:", obs0["market"]["inventory"])
print("Market Prices   :", obs0["market"]["prices"])

# Step 1: Player 0 executes a bulk BUY order for WHEAT (e.g. 50 wheat)
# In kaggriculture, seed/crop buying is via market orders: ["BUY", product, quantity] or ["BUY_SEED", product, quantity]
act0 = {"market": [["BUY", "WHEAT", 50]]}
act1 = {"farmer": ["PASS"]}

env.step([act0, act1])

obs1_p0 = env.state[0]["observation"]
obs1_p1 = env.state[1]["observation"]

print("\n=== AFTER PLAYER 0 BUYS 50 WHEAT ===")
print("P0 Money:", obs1_p0["farms"][0]["money"])
print("P0 Shed :", obs1_p0["private"]["shed"].get("WHEAT"))
print("Market Inventory as seen by P0:", obs1_p0["market"]["inventory"]["WHEAT"])
print("Market Inventory as seen by P1:", obs1_p1["market"]["inventory"]["WHEAT"])
print("Market Prices as seen by P1   :", obs1_p1["market"]["prices"]["WHEAT"])

# Check if inventory replenishment occurs over next 24 steps
print("\n=== STEPPING 24 STEPS (DAY 1) TO OBSERVE REPLENISHMENT ===")
for s in range(24):
    env.step([{"farmer": ["PASS"]}, {"farmer": ["PASS"]}])
    
obs25 = env.state[0]["observation"]
print("Step 25 Market Inventory WHEAT:", obs25["market"]["inventory"]["WHEAT"])
print("Step 25 Market Price WHEAT    :", obs25["market"]["prices"]["WHEAT"])
