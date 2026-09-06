import os, sys, json
import kaggle_environments

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json" # Match 14
with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
opp_actions = [steps[s][1].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture")
import submission_rc6_d1

# Test RC6_D1
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()
for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[0].observation
    act = submission_rc6_d1.agent(obs)
    env.step([act, opp_actions[s]])
print("RC6_D1 final score:", env.state[0].observation["farms"][0]["money"])

# Test rc6_opp_gate
with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f:
    rc6_code = f.read()

target = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    for animal in ("COW", "SHEEP"):"""

replacement = """    remaining_animal_slots = _animal_purchase_cap()
    shed_animals = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
    opp_money = float(_get(_get(obs, "farms", [])[1 - player], "money", 0))
    for animal in ("COW", "SHEEP"):
        if day > 10 and opp_money > 8000: break"""

code = rc6_code.replace(target, replacement)
import types
mod = types.ModuleType("gate_mod")
exec(code, mod.__dict__)

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()
diffs = []
for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[0].observation
    act = mod.agent(obs)
    env.step([act, opp_actions[s]])
print("rc6_opp_gate final score:", env.state[0].observation["farms"][0]["money"])
