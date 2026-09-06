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

# Change 1: Wheat last_plant = 27
c1 = base_code.replace(
    '"WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 24}',
    '"WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False, "last_plant": 27}'
)

# Change 2: Collect fertilizer prio 2, ev 1.5
c2 = base_code.replace(
    'tasks.append(_task(4, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 0.95))',
    'tasks.append(_task(2, (x, y), ["COLLECT_FERTILIZER"], None, "fertilizer", p_fert * 1.5))'
)

# Change 3: Fert reserve = 2
c3 = base_code.replace(
    'fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0',
    'fert_reserve = min(fertilizer, 2) if p_straw >= 70.0 and day <= 24 else 0'
)

# Change 4: Wheat buffer = animal_count + 1, liquidate day 28
c4 = base_code.replace(
    'wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)',
    'wheat_feed_buffer = 0 if day >= 28 else (animal_count + 1)'
)

variants = {
    "Baseline RC12": base_code,
    "+Change 1 (Wheat last_plant 27)": c1,
    "+Change 2 (Fert task prio 2)": c2,
    "+Change 3 (Fert reserve min 2)": c3,
    "+Change 4 (Wheat buffer & Day28 liq)": c4,
}

for name, code_str in variants.items():
    globs = {}
    exec(code_str, globs)
    agent_fn = globs["agent"]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        act = agent_fn(obs)
        env.step([act, opp_actions[s]])
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    print(f"{name:<40} -> Final Score: ${final_score:,}")
