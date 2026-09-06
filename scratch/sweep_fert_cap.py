import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    base_code = f.read()

# Safe Day 28-29 wheat liquidation
base_code = base_code.replace(
    'wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)',
    'wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))'
)

for cap in [8, 10, 12, 14, 16, 18, 20, 25, 999]:
    old_fert = 'fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0'
    new_fert = f'fert_reserve = min(fertilizer, min({cap}, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0'
    code = base_code.replace(old_fert, new_fert)
    globs = {}
    exec(code, globs)
    agent_fn = globs["agent"]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        act = agent_fn(obs)
        env.step([act, opp_actions[s]])
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    print(f"Fertilizer Reserve Cap={cap:<4} -> Match 9 Score: ${final_score:,}")
