import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments
import submission_challenger_exp208_clean as challenger

seed = 1624303674 # The exact seed from Episode 104379472

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

print(f"=========================================================================================")
print(f"     FORENSIC SIMULATION ON EXACT LOSS SEED: {seed}                                      ")
print(f"=========================================================================================")

# Let's inspect initial market prices on seed 1624303674
obs0 = env.state[0].observation
mkt = obs0.get("market", {})
prices = mkt.get("prices", {})
print("Seed 1624303674 Initial Market Prices:", prices)

# Trace our candidate on Seat 1 (as in the real game)
challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

step_num = 0
cash_history = []
straw_shed_history = []
milk_shed_history = []
fert_shed_history = []

while not env.done:
    # Seat 1: Challenger
    obs1 = env.state[1].observation
    act1 = challenger.agent(obs1)
    
    # Let's see what happens if opponent does a passive or standard policy
    # We will record our farm telemetry
    farm1 = obs1.get("farms", [])[1]
    priv1 = obs1.get("private", {})
    shed1 = priv1.get("shed", {})
    
    if step_num % 24 == 0:
        day = step_num // 24
        money = farm1.get("money", 0)
        unlocked = farm1.get("unlocked_quadrants", [])
        hands = farm1.get("hands", [])
        straw_in_shed = shed1.get("STRAWBERRY", 0)
        milk_in_shed = shed1.get("MILK", 0)
        fert_in_shed = shed1.get("FERTILIZER", 0)
        cur_prices = obs1.get("market", {}).get("prices", {})
        print(f"Day {day:2d} (Step {step_num:3d}): Cash ${money:7.1f} | Lands: {len(unlocked)} | Workers: {len(hands):2d} | Shed: [Straw:{straw_in_shed:2d}, Milk:{milk_in_shed:2d}, Fert:{fert_in_shed:2d}] | P_straw: ${cur_prices.get('STRAWBERRY', 0):3.0f} | P_milk: ${cur_prices.get('MILK', 0):3.0f}")
        
    actions = [{"farmer": ["PASS"], "hands": [], "market": []}, act1]
    env.step(actions)
    step_num += 1

final_reward = env.state[1].reward
print(f"\nFinal Reward on Seed {seed}: ${final_reward:,.1f}")
