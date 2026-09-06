import os, sys, json
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

import concurrent.futures

def inspect_match(args):
    idx, (rp, hero_seat) = args
    sys.path.insert(0, r"D:\kaggriculture")
    import submission_rc12
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    info_d11 = {}
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        if day == 11 and not info_d11:
            prices = obs["market"]["prices"]
            farm = obs["farms"][hero_seat]
            strawberries = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            melons = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "MELON")
            wheat = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "WHEAT")
            shed = obs["private"]["shed"]
            info_d11 = {
                "money": farm["money"],
                "p_straw": prices.get("STRAWBERRY"),
                "p_milk": prices.get("MILK"),
                "p_wool": prices.get("WOOL"),
                "p_melon": prices.get("MELON"),
                "strawberries": strawberries,
                "melons": melons,
                "wheat": wheat,
                "shed_wheat": shed.get("WHEAT", 0),
                "shed_fert": shed.get("FERTILIZER", 0),
            }
        act = submission_rc12.agent(obs)
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    return idx, final_score, info_d11

if __name__ == "__main__":
    tasks = [(i+1, m) for i, m in enumerate(SELECTED_REPLAYS)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(inspect_match, tasks))
    print(f"{'#':<3} | {'Score':<7} | {'Money D11':<9} | {'P_Straw':<7} | {'P_Milk':<6} | {'P_Wool':<6} | {'P_Melon':<7} | {'St#':<3} | {'W#':<3} | {'ShedW':<5}")
    print("-" * 75)
    for idx, score, info in sorted(res, key=lambda x: x[0]):
        print(f"#{idx:02d} | ${score:>6,d} | ${info['money']:>7,.0f} | ${info['p_straw']:>5} | ${info['p_milk']:>4} | ${info['p_wool']:>4} | ${info['p_melon']:>5} | {info['strawberries']:>3d} | {info['wheat']:>3d} | {info['shed_wheat']:>5d}")
