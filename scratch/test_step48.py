import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

obs = {"day": 2, "hour": 0, "player": 1, "step": 48}
act = challenger.agent(obs)
print("Action at day 2, hour 0, step 48:", act)
