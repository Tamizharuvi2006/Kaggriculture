import kaggle_environments

seeds = {
    "104522963 (WIN +16k vs 881)": 210854550,
    "104522548 (LOSS -12k vs 915)": 944832403,
    "104524295 (LOSS -1.4k vs 871)": 1891809261,
    "104523414 (LOSS -11k vs 861)": 836077564,
    "104526077 (LOSS -9.2k vs 841)": 773315358,
}

print("=" * 90)
print(f"{'Match Label':<32} | {'Seed':<12} | {'Fert D0':<8} | {'Milk D0':<8} | {'Wool D0':<8} | {'Straw D0':<8}")
print("-" * 90)

for label, seed in seeds.items():
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    obs = env.state[0].observation
    mkt = obs.market["prices"]
    p_fert = mkt.get("FERTILIZER", 0)
    p_milk = mkt.get("MILK", 0)
    p_wool = mkt.get("WOOL", 0)
    p_straw = mkt.get("STRAWBERRY", 0)
    print(f"{label:<32} | {seed:<12} | ${p_fert:<7.1f} | ${p_milk:<7.1f} | ${p_wool:<7.1f} | ${p_straw:<7.1f}")
print("=" * 90)
