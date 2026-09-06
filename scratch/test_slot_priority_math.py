import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"seed": 42})
env.reset()

env.state[0].observation.private["shed"]["MILK"] = 10
env.state[1].observation.private["shed"]["MILK"] = 10
env.state[1].observation.private["shed"]["CARROT"] = 10

# Test Case 1: P0 sells MILK at Slot 0. P1 sells CARROT at Slot 0, then MILK at Slot 1.
act0 = {"market": [["SELL", "MILK", 10]]}
act1 = {"market": [["SELL", "CARROT", 10], ["SELL", "MILK", 10]]}

p_carrot_start = env.state[0].observation.market["prices"]["CARROT"]
p_milk_start = env.state[0].observation.market["prices"]["MILK"]

env.step([act0, act1])

p0_earned_slot0 = env.state[0].observation.farms[0]["money"] - 3000
# In act1, 10 carrots were sold in slot 0. Let's see what they sold for:
# Carrot inventory was 10000. 10 carrots sold -> 10 * 35 = 350.
total_p1 = env.state[1].observation.farms[1]["money"] - 3000

# Test Case 2: Control where BOTH players sell MILK at Slot 0 simultaneously
env2 = kaggle_environments.make("kaggriculture", configuration={"seed": 42})
env2.reset()
env2.state[0].observation.private["shed"]["MILK"] = 10
env2.state[1].observation.private["shed"]["MILK"] = 10
act0_c = {"market": [["SELL", "MILK", 10]]}
act1_c = {"market": [["SELL", "MILK", 10]]}
env2.step([act0_c, act1_c])

p0_c_slot0 = env2.state[0].observation.farms[0]["money"] - 3000
p1_c_slot0 = env2.state[1].observation.farms[1]["money"] - 3000

print(f"Starting Milk Price: {p_milk_start}")
print("--- TEST CASE 1: P0 sells Milk in Slot 0, P1 sells Milk in Slot 1 ---")
print(f"P0 earned from Milk (Slot 0): {p0_earned_slot0} (avg {p0_earned_slot0/10:.2f}/u)")
print(f"P1 total earned (Carrot slot 0 + Milk slot 1): {total_p1}")
p1_milk_only = total_p1 - (10 * 35) # approximate
print(f"P1 earned from Milk (Slot 1): {p1_milk_only} (avg {p1_milk_only/10:.2f}/u)")
print(f"ADVANTAGE TO SLOT 0 SELLER: +{p0_earned_slot0 - p1_milk_only} coins (+{(p0_earned_slot0 - p1_milk_only)/p0_earned_slot0*100:.1f}%)!")
print()
print("--- TEST CASE 2: CONTROL (Both players sell Milk in Slot 0 simultaneously) ---")
print(f"P0 earned: {p0_c_slot0} | P1 earned: {p1_c_slot0}")
print(f"Difference in simultaneous Slot 0: {p0_c_slot0 - p1_c_slot0} coins")
