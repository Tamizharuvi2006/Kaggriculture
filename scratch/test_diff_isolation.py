import os, sys, json
import kaggle_environments

SELECTED_REPLAYS = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0), # Match 1
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1), # Match 2
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0), # Match 14
]

def run_mod(mod, replay_path, hero_seat):
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        act = mod.agent(obs)
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
    return int(env.state[hero_seat].observation["farms"][hero_seat]["money"])

with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    base_code = f.read()

# Variant A: RC12 + Day 11 Cow Only
code_cow = base_code.replace(
"""    for animal in ("COW", "SHEEP"):
        # Day-10 Amortization Horizon: Never buy animals after Day 10 (cows take 8+ days to yield!)
        if day > 10: break""",
"""    # Dynamic Herd Carrying Capacity check:
    tiles = farm.get("tiles", [])
    wheat_plots = sum(1 for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
    current_herd = counts["COW"] + counts["SHEEP"]
    max_carrying_capacity = max(4, int(wheat_plots * 1.5))

    for animal in ("COW", "SHEEP"):
        if day > 11: break
        if day == 11:
            if animal != "COW" or budget < 10000 or current_herd >= max_carrying_capacity:
                continue"""
)

# Variant B: RC12 + Wheat Day 28 only
code_wheat = base_code.replace(
"""    wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)""",
"""    wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))"""
)

# Variant C: RC12 + Fert Reserve (min 14) only
code_fert = base_code.replace(
"""    fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0""",
"""    fert_reserve = min(fertilizer, min(14, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0"""
)

import types
def load_code(code, name):
    m = types.ModuleType(name)
    exec(code, m.__dict__)
    return m

m_base = load_code(base_code, "rc12_base")
m_cow = load_code(code_cow, "rc12_cow")
m_wheat = load_code(code_wheat, "rc12_wheat")
m_fert = load_code(code_fert, "rc12_fert")

if __name__ == "__main__":
    for name, m in [("RC12 Base", m_base), ("RC12 + Cow Day 11", m_cow), ("RC12 + Wheat Day 28", m_wheat), ("RC12 + Fert min(14)", m_fert)]:
        print(f"--- {name} ---")
        for idx, (rp, seat) in enumerate(SELECTED_REPLAYS):
            s = run_mod(m, rp, seat)
            print(f"  Match {idx+1}: {s}")
