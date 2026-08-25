"""Analyze shop unlock sequence vs Total Market Pie across all 32 holdout seeds."""
import os
import sys
import kaggle_environments
import numpy as np

seeds = [
    42, 100, 2026, 590244349, 999999, 12345, 777777, 888888,
    11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888,
    10101, 20202, 30303, 40404, 50505, 60606, 70707, 80808,
    90909, 12121, 23232, 34343, 45454, 56565, 67676, 78787
]

straw_shops = {"SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET"}

print("=========================================================================================================")
print("SHOP UNLOCK SEQUENCE vs TOTAL SHARED PIE ACROSS 32 SEEDS")
print("=========================================================================================================")
print(f"{'Seed':>10} | {'Day 5 Unlocked Shops':<40} | {'Day 10 Unlocked Shops':<40}")
print("-" * 105)

for s in seeds[:10]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s})
    env.reset()
    
    shops_day5 = []
    shops_day10 = []
    for step in range(241):
        obs = env.state[0].observation
        if step == 120:
            shops_day5 = list(obs.get("town", {}).get("unlocked_shops", []))
        if step == 240:
            shops_day10 = list(obs.get("town", {}).get("unlocked_shops", []))
        env.step([{"farmer": ["PASS"], "market": []}, {"farmer": ["PASS"], "market": []}])
        
    print(f"{s:>10} | {str(shops_day5):<40} | {str(shops_day10):<40}")
