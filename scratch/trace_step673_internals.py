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
    if step_num == 673:
        step = min(max(0, int(old_mod._get(obs, "step", 0))), len(old_mod._V18_RUNTIME["experts"]["mohit"]["actions"]) - 1)
        raw_old = old_mod._v18_closed_loop_action(obs, step)
        raw_new = new_mod._v18_closed_loop_action(obs, step)
        print("step:", step)
        print("raw_old market:", raw_old.get("market"))
        print("raw_new market:", raw_new.get("market"))
        
        overlaid_old = old_mod._copy_action(raw_old)
        overlaid_new = new_mod._copy_action(raw_new)
        
        adapt_old = old_mod._apply_fixed_board_adaptation(obs, overlaid_old)
        adapt_new = new_mod._apply_fixed_board_adaptation(obs, overlaid_new)
        print("adapt_old market:", adapt_old.get("market"))
        print("adapt_new market:", adapt_new.get("market"))
        break
        
    act = old_mod.agent(obs)
    other_seat = 1 - seat
    actions = [None, None]
    actions[seat] = act
    actions[other_seat] = {"farmer": ["PASS"], "hands": [], "market": []}
    env.step(actions)
    step_num += 1
