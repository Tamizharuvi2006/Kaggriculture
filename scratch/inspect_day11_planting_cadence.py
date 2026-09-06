import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2

seed = 628719714
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

print("=" * 80)
print("RC2 EXPANSION PLANTING CADENCE (DAYS 11 TO 16):")
print("=" * 80)

for s in range(11 * 24, 16 * 24):
    day = s // 24
    hour = s % 24
    obs = env.state[0].observation
    f = obs.farms[0]
    
    straw_tiles = sum(1 for r in f.tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
    empty_tiles = sum(1 for r in f.tiles for t in r if t is None)
    
    act0 = rc2.agent(obs)
    act1 = rc2.agent(env.state[1].observation)
    
    # Check seed purchases
    mkt = act0.get("market", []) if isinstance(act0, dict) else []
    straw_seeds_bought = sum(o[2] for o in mkt if len(o) >= 3 and o[0] == "BUY_SEED" and o[1] == "STRAWBERRY")
    
    if hour in (0, 6, 12, 18) or straw_seeds_bought > 0:
        print(f"Day {day:02d} Hr {hour:02d} | Straw Bushes in Ground: {straw_tiles:>2} | Empty Arable Tiles: {empty_tiles:>2} | Seeds Bought: {straw_seeds_bought:>2} | Money: ${f.money:,.0f}")
        
    env.step([act0, act1])
