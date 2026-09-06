import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture")
import submission_rc12
sys.path.insert(0, r"D:\kaggriculture\scratch")
import candidate_rc15_v1

for name, mod in [("RC12", submission_rc12), ("RC15_v1", candidate_rc15_v1)]:
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        if day == 21 and hour >= 18:
            act = mod.agent(obs)
            units_acts = [act.get("farmer", [])] + act.get("hands", [])
            drops = sum(1 for a in units_acts if a and a[0] == "DROP")
            moves = sum(1 for a in units_acts if a and a[0] in ("NORTH", "SOUTH", "EAST", "WEST"))
            ferts = sum(1 for a in units_acts if a and a[0] == "COLLECT_FERTILIZER")
            print(f"{name} D21 H{hour}: Drops={drops}, Moves={moves}, CollectFert={ferts}")
        else:
            act = mod.agent(obs)
        env.step([act, opp_actions[s]])
