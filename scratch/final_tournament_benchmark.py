import os, sys, json
import kaggle_environments
import concurrent.futures
import numpy as np

sys.path.insert(0, r"D:\kaggriculture")

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

def _eval_match_pair(args):
    rp, seat = args
    with open(rp, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    import submission_rc12
    import submission_rc15
    
    results = {}
    for mod, name in [(submission_rc12, "rc12"), (submission_rc15, "rc15")]:
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
        env.reset()
        for s in range(len(steps)-1):
            if env.done: break
            obs = env.state[seat].observation
            act = mod.agent(obs)
            if seat == 0:
                env.step([act, opp_actions[s]])
            else:
                env.step([opp_actions[s], act])
        results[name] = int(env.state[seat].observation["farms"][seat]["money"])
    return results

if __name__ == "__main__":
    tasks = [(rp, seat) for rp, seat in SELECTED_REPLAYS]
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as ex:
        all_results = list(ex.map(_eval_match_pair, tasks))
        
    s12 = [r["rc12"] for r in all_results]
    s15 = [r["rc15"] for r in all_results]
    
    print("\n" + "=" * 80)
    print(f"{'Match':>5} | {'RC12 (Baseline)':>16} | {'RC15 (Champion)':>16} | {'Delta':>12} | {'Verdict'}")
    print("=" * 80)
    for i in range(len(s12)):
        d = s15[i] - s12[i]
        tag = "WIN" if d > 0 else ("TIE" if d == 0 else "LOSS")
        print(f"#{i+1:02d}   | ${s12[i]:>14,d} | ${s15[i]:>14,d} | ${d:>+10,d} | {tag}")
    print("=" * 80)
    
    # Statistical Summary
    np.random.seed(42)
    boot_means_12 = [np.mean(np.random.choice(s12, size=len(s12), replace=True)) for _ in range(10000)]
    boot_means_15 = [np.mean(np.random.choice(s15, size=len(s15), replace=True)) for _ in range(10000)]
    boot_deltas = [np.mean(np.random.choice(np.array(s15) - np.array(s12), size=len(s12), replace=True)) for _ in range(10000)]
    
    ci12 = np.percentile(boot_means_12, [2.5, 97.5])
    ci15 = np.percentile(boot_means_15, [2.5, 97.5])
    ci_delta = np.percentile(boot_deltas, [2.5, 97.5])
    
    print("\n--- STATISTICAL TOURNAMENT BENCHMARK (20 EPISODES, 10 WORKERS) ---")
    print(f"RC12 Baseline: Mean ${np.mean(s12):>7,.0f} [95% CI: ${ci12[0]:>6,.0f} - ${ci12[1]:>6,.0f}] | Floor: ${min(s12):>6,d} | Ceiling: ${max(s12):>6,d}")
    print(f"RC15 Champion: Mean ${np.mean(s15):>7,.0f} [95% CI: ${ci15[0]:>6,.0f} - ${ci15[1]:>6,.0f}] | Floor: ${min(s15):>6,d} | Ceiling: ${max(s15):>6,d}")
    print(f"Mean Delta:    ${np.mean(s15) - np.mean(s12):>+7,.0f} [95% CI: ${ci_delta[0]:>+6,.0f} - ${ci_delta[1]:>+6,.0f}]")
    print(f"Wins / Ties / Losses: {sum(1 for d in np.array(s15)-np.array(s12) if d > 0)} / {sum(1 for d in np.array(s15)-np.array(s12) if d == 0)} / {sum(1 for d in np.array(s15)-np.array(s12) if d < 0)}")
