import os, sys, json, time
import concurrent.futures
import kaggle_environments

SELECTED_REPLAYS = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 1),
    (r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json", 1),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91296662\episode-91296662-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91297572\episode-91297572-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91333120\episode-91333120-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91341377\episode-91341377-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91694495\episode-91694495-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\92602112\episode-92602112-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\92603055\episode-92603055-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95511283\episode-95511283-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95579586\episode-95579586-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95622859\episode-95622859-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95702913\episode-95702913-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95773643\episode-95773643-replay.json", 0),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95775674\episode-95775674-replay.json", 0),
]

def _run_match(args):
    replay_path, hero_seat = args
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc12
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    fert_sold = 0
    wheat_sold = 0
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        act = submission_rc12.agent(obs)
        for o in act.get("market", []):
            if o and o[0] == "SELL":
                if o[1] == "FERTILIZER": fert_sold += o[2]
                elif o[1] == "WHEAT": wheat_sold += o[2]
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    end_shed = env.state[hero_seat].observation["private"]["shed"]
    return {
        "score": final_score,
        "fert_sold": fert_sold,
        "wheat_sold": wheat_sold,
        "end_fert_shed": end_shed.get("FERTILIZER", 0),
        "end_wheat_shed": end_shed.get("WHEAT", 0),
    }

if __name__ == "__main__":
    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(_run_match, SELECTED_REPLAYS))
    print(f"Done in {time.time()-t0:.2f}s across 10 workers")
    scores = [r["score"] for r in res]
    print(f"Mean: ${sum(scores)/len(scores):,.0f} | Min: ${min(scores):,} | Max: ${max(scores):,}")
    for i, r in enumerate(res):
        print(f"#{i+1:02d}: Score=${r['score']:>6,d} | Fert Sold={r['fert_sold']:>3d}, Shed={r['end_fert_shed']:>2d} | Wheat Sold={r['wheat_sold']:>3d}, Shed={r['end_wheat_shed']:>2d}")
