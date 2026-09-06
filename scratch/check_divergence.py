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
    sells = {d: [] for d in range(30)}
    buys = {d: [] for d in range(30)}
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        act = mod.agent(obs)
        for o in act.get("market", []):
            if o and o[0] == "SELL":
                sells[day].append((o[1], o[2]))
            elif o and o[0].startswith("BUY"):
                if len(o) > 1:
                    buys[day].append((o[0], o[1], o[2] if len(o) > 2 else 1))
                else:
                    buys[day].append((o[0], "LAND", 1))
        env.step([act, opp_actions[s]])
    print(f"=== {name} Buys and Sells Days 20-25 ===")
    for d in range(20, 26):
        b_str = ", ".join(f"{b[1]}x{b[2]}" for b in buys[d][:5])
        s_str = ", ".join(f"{s[0]}x{s[1]}" for s in sells[d][:5])
        print(f"  Day {d:02d} Buys: [{b_str}] | Sells: [{s_str}]")
