import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208 as old_mod
import submission_challenger_exp208_clean as new_mod

seed = 2000004
seat = 0

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

step_num = 0
while not env.done:
    obs = env.state[seat].observation
    act_old = old_mod.agent(obs)
    act_new = new_mod.agent(obs)
    
    if old_mod._V18_SELECTED_MARKET != new_mod._V18_SELECTED_MARKET:
        print(f"--- DIVERGENCE AT STEP {step_num} (Day {step_num // 24}) ---")
        print("old_mod._V18_SELECTED_MARKET:", old_mod._V18_SELECTED_MARKET)
        print("new_mod._V18_SELECTED_MARKET:", new_mod._V18_SELECTED_MARKET)
        print("old_mod state features:", old_mod._v18_state_features(obs))
        print("new_mod state features:", new_mod._v18_state_features(obs))
        break
        
    other_seat = 1 - seat
    actions = [None, None]
    actions[seat] = act_old
    actions[other_seat] = {"farmer": ["PASS"], "hands": [], "market": []}
    env.step(actions)
    step_num += 1
