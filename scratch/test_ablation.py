import os, sys, json, time
import kaggle_environments

SELECTED_REPLAYS = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0), # Match 1
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1), # Match 2
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1), # Match 4
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0), # Match 14
]

def run_sim(mod_name, replay_path, hero_seat):
    if mod_name in sys.modules: del sys.modules[mod_name]
    mod = __import__(mod_name)
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

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    for m in ["submission_rc12", "submission_rc15"]:
        print(f"Running {m}:")
        for idx, (rp, seat) in enumerate(SELECTED_REPLAYS):
            s = run_sim(m, rp, seat)
            print(f"  Match {idx+1}: {s}")
