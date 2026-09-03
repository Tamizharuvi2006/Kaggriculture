import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208_clean as new_mod

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()
obs0 = env.state[0].observation

print("NEW STRATEGY:", new_mod.STRATEGY)

player = int(new_mod._get(obs0, "player", 0))
print("player:", player)

seat = 1 if player == 1 else 0
print("seat:", seat)

experts = new_mod._V18_RUNTIME["experts"]
base_board_name = new_mod._V18_RUNTIME["board_by_seat"][str(seat)]
print("base_board_name:", base_board_name)

raw = new_mod._v18_closed_loop_action(obs0, 0)
print("raw:", raw)
