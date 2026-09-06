import kaggle_environments

env = kaggle_environments.make("kaggriculture", configuration={"seed": 42})
env.reset()

# Inject 10 milk and 10 carrot into both sheds
env.state[0].observation.private["shed"]["MILK"] = 10
env.state[0].observation.private["shed"]["CARROT"] = 10
env.state[1].observation.private["shed"]["MILK"] = 10
env.state[1].observation.private["shed"]["CARROT"] = 10

m0_before = env.state[0].observation.farms[0]["money"]
m1_before = env.state[1].observation.farms[1]["money"]
p_milk_before = env.state[0].observation.market["prices"]["MILK"]

# Player 0 puts MILK at Slot 0
act0 = {"market": [["SELL", "MILK", 10]]}
# Player 1 puts CARROT at Slot 0, and MILK at Slot 1
act1 = {"market": [["SELL", "CARROT", 10], ["SELL", "MILK", 10]]}

env.step([act0, act1])

m0_after = env.state[0].observation.farms[0]["money"]
m1_after = env.state[1].observation.farms[1]["money"]
p_milk_after = env.state[0].observation.market["prices"]["MILK"]

# In Slot 0, Player 1 sold 10 carrots. Let's see what each earned!
p0_milk_earned = m0_after - m0_before
# What did Player 1 earn from carrot and milk?
# Let's inspect exact transaction amounts:
print(f"Starting Milk Price: ${p_milk_before:,.2f}")
print(f"Player 0 earned from MILK (Slot 0): ${p0_milk_earned:,.2f} (Avg: ${p0_milk_earned/10:.2f}/unit)")
print(f"Player 1 total earned (Carrot in Slot 0 + Milk in Slot 1): ${m1_after - m1_before:,.2f}")
print(f"Ending Milk Spot Price: ${p_milk_after:,.2f}")
