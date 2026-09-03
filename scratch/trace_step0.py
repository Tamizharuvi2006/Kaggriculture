import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208 as old_mod

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()
obs0 = env.state[0].observation

print("STRATEGY:", old_mod.STRATEGY)
print("use_fixed_schedule:", old_mod.STRATEGY.get("use_fixed_schedule"))
print("version:", old_mod.STRATEGY.get("fixed_schedule_version"))

# Step through old_mod._base_agent
version = old_mod.STRATEGY.get("fixed_schedule_version")
player = int(old_mod._get(obs0, "player", 0))
print("player:", player)

board_name = old_mod._V18_RUNTIME["board_by_seat"][str(1 if player == 1 else 0)]
print("board_name:", board_name)
schedule = old_mod._V18_RUNTIME["experts"][board_name]["actions"]
print("schedule[0]:", schedule[0])

raw = old_mod._v18_closed_loop_action(obs0, 0)
print("raw:", raw)

overlaid = old_mod._copy_action(raw)
final_base = old_mod._apply_fixed_board_adaptation(obs0, overlaid)
print("final_base:", final_base)
