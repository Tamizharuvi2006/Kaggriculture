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

with open(r"D:\kaggriculture\submission_rc12.py", "r", encoding="utf-8") as f:
    base_code = f.read()

# Variant A: Safe Wheat Liquidation on Day 28 (1-day buffer on D28, 0 on D29)
code_va = base_code.replace(
    'wheat_feed_buffer = 0 if day >= 29 else (animal_count * 2 + 2)',
    'wheat_feed_buffer = 0 if day >= 29 else (animal_count if day >= 28 else (animal_count * 2 + 2))'
)

# Variant B: Fertilizer Reserve capped at 6 (monetize surplus above 6)
code_vb = base_code.replace(
    'fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0',
    'fert_reserve = min(fertilizer, min(6, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0'
)

# Variant C: Both A and B
code_vc = code_va.replace(
    'fert_reserve = min(fertilizer, len(_fertilizer_positions(obs))) if p_straw >= 70.0 and day <= 24 else 0',
    'fert_reserve = min(fertilizer, min(6, len(_fertilizer_positions(obs)))) if p_straw >= 70.0 and day <= 24 else 0'
)

with open(r"D:\kaggriculture\scratch\cand_va.py", "w", encoding="utf-8") as f: f.write(code_va)
with open(r"D:\kaggriculture\scratch\cand_vb.py", "w", encoding="utf-8") as f: f.write(code_vb)
with open(r"D:\kaggriculture\scratch\cand_vc.py", "w", encoding="utf-8") as f: f.write(code_vc)

def _eval_one(args):
    mod_name, r_path, seat = args
    sys.path.insert(0, r"D:\kaggriculture\scratch")
    mod = __import__(mod_name)
    with open(r_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[seat].observation
        act = mod.agent(obs)
        env.step([act, opp_actions[s]] if seat == 0 else [opp_actions[s], act])
    return int(env.state[seat].observation["farms"][seat]["money"])

if __name__ == "__main__":
    for vname in ["cand_va", "cand_vb", "cand_vc"]:
        t0 = time.time()
        tasks = [(vname, r_path, seat) for r_path, seat in SELECTED_REPLAYS]
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
            scores = list(ex.map(_eval_one, tasks))
        print(f"=== {vname} in {time.time()-t0:.2f}s ===")
        print(f"Mean: ${sum(scores)/len(scores):,.0f} | Min (Floor): ${min(scores):,} | Max (Ceiling): ${max(scores):,}")
        print(f"Scores: {scores}\n")
