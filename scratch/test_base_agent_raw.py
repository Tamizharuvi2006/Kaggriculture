import sys
sys.path.insert(0, r"D:\kaggriculture")
import kaggle_environments
import submission_challenger_exp208 as old_mod

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": 42})
env.reset()
obs0 = env.state[0].observation

# Call _base_agent directly without try-except block
try:
    version = old_mod.STRATEGY.get("fixed_schedule_version")
    player = int(old_mod._get(obs0, "player", 0))
    print("version:", version)
    board_name = old_mod._V18_RUNTIME["board_by_seat"][str(1 if player == 1 else 0)]
    schedule = old_mod._V18_RUNTIME["experts"][board_name]["actions"]
    step = min(max(0, int(old_mod._get(obs0, "step", 0))), len(schedule) - 1)
    action = schedule[step]
    print("action:", action)
    raw = old_mod._v18_closed_loop_action(obs0, step) if version == "v18" else None
    print("raw:", raw)
except Exception as e:
    print("EXCEPTION IN RAW:", type(e), e)

# Now call old_mod._base_agent
res = old_mod._base_agent(obs0)
print("old_mod._base_agent(obs0) =", res)
