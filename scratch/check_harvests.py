import json, sys
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json"
with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
steps = rep["steps"]
hero_seat = 0
opp_seat = 1
opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]

sys.path.insert(0, r"D:\kaggriculture\scratch")
import candidate_rc15_v1

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
env.reset()

for s in range(len(steps)-1):
    if env.done: break
    obs = env.state[hero_seat].observation
    day = obs["day"]
    hour = obs["hour"]
    if hour == 23 and 20 <= day <= 25:
        shed = obs["private"]["shed"]
        invs = obs["private"]["inventories"]
        total_straw_inv = sum(inv.get("STRAWBERRY", 0) for inv in invs)
        total_milk_inv = sum(inv.get("MILK", 0) for inv in invs)
        tiles = obs["farms"][hero_seat]["tiles"]
        straw_tiles = [t for r in tiles for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY"]
        unharvested_straw_yield = sum(t.get("yield_units", 0) for t in straw_tiles)
        watered_straw = sum(1 for t in straw_tiles if t.get("watered_today"))
        print(f"End of Day {day:02d}: Straw Shed={shed.get('STRAWBERRY', 0):2d}, Inv={total_straw_inv:2d}, Unharvested={unharvested_straw_yield:2d}, Watered={watered_straw:2d}/{len(straw_tiles):2d} | Milk Shed={shed.get('MILK', 0):2d}, Inv={total_milk_inv:2d}")
    act = candidate_rc15_v1.agent(obs)
    env.step([act, opp_actions[s]])
