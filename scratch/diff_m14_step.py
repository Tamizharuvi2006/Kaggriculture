import json, kaggle_environments, types, sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_rc6_d1

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json"
with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
opp_actions = [steps[s][1].get("action") for s in range(1, len(steps))]

with open(r"D:\kaggriculture\submission_rc6_d1.py", "r", encoding="utf-8") as f: code = f.read()
target = """    for animal in ("COW", "SHEEP"):"""
repl = """    opp_money = float(_get(_get(obs, "farms", [])[1 - player], "money", 0))
    for animal in ("COW", "SHEEP"):
        if day > 10 and opp_money > 8000: break"""
mod = types.ModuleType("gate_mod")
exec(code.replace(target, repl), mod.__dict__)

env1 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env2 = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env1.reset(); env2.reset()

for s in range(len(steps)-1):
    if env1.done: break
    o1 = env1.state[0].observation
    o2 = env2.state[0].observation
    a1 = submission_rc6_d1.agent(o1)
    a2 = mod.agent(o2)
    if a1 != a2:
        print(f"Diff at step {s} (Day {s//24}):")
        print("  RC6: ", a1.get("market"))
        print("  Gate:", a2.get("market"))
        break
    env1.step([a1, opp_actions[s]])
    env2.step([a2, opp_actions[s]])
