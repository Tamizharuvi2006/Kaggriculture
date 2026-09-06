import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments

# Let's inspect town consumption parameters from the engine
env = kaggle_environments.make("kaggriculture", configuration={"seed": 42})
env.reset()
town = env.state[0].observation.town
shops = town.get("unlocked_shops", [])
print(f"Town unlocked shops at start: {shops}")

# How many shops consume STRAWBERRY?
# From engine SHOPS dictionary:
# BAKERY: WHEAT, CARROT
# GROCERY: STRAWBERRY, TOMATO, CARROT, MELON
# RESTAURANT: MILK, EGG, WOOL, MEAT...
# Let's check which shops have STRAWBERRY:
from kaggle_environments.envs.kaggriculture.kaggriculture import SHOPS

straw_shops = [s for s, prods in SHOPS.items() if "STRAWBERRY" in prods]
print(f"Shops that consume STRAWBERRY: {straw_shops}")

# Count how many of these shops are unlocked across episodes
straw_shop_count = sum(1 for s in shops if "STRAWBERRY" in SHOPS.get(s, []))
print(f"Number of STRAWBERRY-consuming shops in town: {straw_shop_count}")

# Daily town strawberry consumption capacity:
# Every 4 hours: 1 unit per shop (or 2 if sole product)
# Every 24 hours: 1 unit town center
daily_town_demand = (straw_shop_count * 6) + 1
print(f"Maximum daily town demand for STRAWBERRY: ~{daily_town_demand} units/day")
print(f"Bi-daily town demand (every 2 days):       ~{daily_town_demand * 2} units every 2 days")
print("-" * 80)
print("PRODUCTION VS ABSORPTION BALANCE (Every 2-day harvest cycle):")
for opp_straw in [0, 5, 10, 15, 20, 25, 30]:
    our_straw = 26 # RC2 standard post-Day 11 strawberry allocation
    total_bushes = our_straw + opp_straw
    # Each bush produces 1 strawberry every 2 days
    bi_daily_production = total_bushes
    net_inventory_delta_per_cycle = bi_daily_production - (daily_town_demand * 2)
    net_per_day = net_inventory_delta_per_cycle / 2
    
    status = "SCARCITY PRESERVED (P ~ $280)" if net_per_day <= 0 else "SATURATION TRAP (P -> $18)"
    print(f"Opponent: {opp_straw:>2} bushes | Total: {total_bushes:>2} bushes | 2-Day Prod: {bi_daily_production:>2} | 2-Day Demand: {daily_town_demand*2:>2} | Net/Day: {net_per_day:>+4.1f} | {status}")
