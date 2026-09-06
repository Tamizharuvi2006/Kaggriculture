import os, sys, json
import kaggle_environments

rp = r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json" # Match 1
hero_seat = 0

def check_straw_tiles():
    import submission_rc12
    import submission_rc6_d1
    
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    for mod, name in [(submission_rc12, "RC12"), (submission_rc6_d1, "RC6_D1")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[hero_seat].observation
            d = obs["day"]
            h = s % 24
            if h == 0 and d in [10, 11, 12, 13, 14, 15, 20, 25]:
                farm = obs["farms"][hero_seat]
                straw_coords = set((x, y) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row) if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
                pasture_coords = set((x, y) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row) if isinstance(t, dict) and t.get("kind") == "PASTURE")
                print(f"[{name}] Day {d:02d}: {len(straw_coords)} strawberries | {len(pasture_coords)} pastures")
                if d == 12:
                    print(f"  [{name}] Pasture coords D12:", sorted(list(pasture_coords)))
            act = mod.agent(obs)
            if hero_seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    check_straw_tiles()
