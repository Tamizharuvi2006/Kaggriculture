import json, sys, time
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

def _inspect_one(args):
    replay_path, hero_seat = args
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc6_d1
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    d11_money = None
    d11_wheat = None
    d11_wheat_plots = None
    d11_buys = []
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        hour = obs["hour"]
        if day == 11 and hour == 0:
            farm = obs["farms"][hero_seat]
            d11_money = farm["money"]
            d11_wheat = obs["private"]["shed"].get("WHEAT", 0)
            d11_wheat_plots = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
        act = submission_rc6_d1.agent(obs)
        if day == 11 and hour == 0:
            for o in act.get("market", []):
                if o and o[0] == "BUY_ANIMAL":
                    d11_buys.append(f"{o[1]}x{o[2]}")
        env.step([act, opp_actions[s]] if hero_seat == 0 else [opp_actions[s], act])
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    return {
        "final": final_score,
        "d11_money": d11_money,
        "d11_wheat": d11_wheat,
        "d11_wheat_plots": d11_wheat_plots,
        "d11_buys": d11_buys
    }

if __name__ == "__main__":
    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(_inspect_one, SELECTED_REPLAYS))
    print(f"Inspection completed in {time.time()-t0:.2f}s across 10 workers")
    print(f"{'Match':<6} | {'RC6_D1 Final':<12} | {'D11 Money':<10} | {'D11 Shed Wheat':<14} | {'D11 Wheat Plots':<15} | {'D11 Buys':<25}")
    for i, r in enumerate(res):
        b_str = ", ".join(r["d11_buys"]) if r["d11_buys"] else "None"
        m_str = f"${r['d11_money']:>8,.0f}" if r['d11_money'] is not None else "N/A"
        w_str = f"{r['d11_wheat']:>14d}" if r['d11_wheat'] is not None else "N/A"
        wp_str = f"{r['d11_wheat_plots']:>15d}" if r['d11_wheat_plots'] is not None else "N/A"
        print(f"#{i+1:02d}    | ${r['final']:>10,d} | {m_str} | {w_str} | {wp_str} | {b_str:<25}")
