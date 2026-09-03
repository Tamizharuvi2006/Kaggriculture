import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208 as old_mod
import submission_challenger_exp208_clean as new_mod

seed = 2000004
seat = 0

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

old_mod._V18_SELECTED_MARKET = {0: None, 1: None}
old_mod._V18_SELECTED_DAY = {0: None, 1: None}
old_mod._V18_SELECTED_BOARD = {0: None, 1: None}
new_mod._V18_SELECTED_MARKET = {0: None, 1: None}
new_mod._V18_SELECTED_DAY = {0: None, 1: None}
new_mod._V18_SELECTED_BOARD = {0: None, 1: None}

step_num = 0
while not env.done:
    obs = env.state[seat].observation
    act_old = old_mod.agent(obs)
    act_new = new_mod.agent(obs)
    
    if act_old != act_new or step_num == 673:
        print(f"--- STEP {step_num} ---")
        print("OLD _base_agent:", old_mod._base_agent(obs))
        print("NEW _base_agent:", new_mod._base_agent(obs))
        print("OLD agent:", act_old)
        print("NEW agent:", act_new)
        break
        
    other_seat = 1 - seat
    actions = [None, None]
    actions[seat] = act_old
    actions[other_seat] = {"farmer": ["PASS"], "hands": [], "market": []}
    env.step(actions)
    step_num += 1
