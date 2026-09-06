import os, sys, json, time
import concurrent.futures
import kaggle_environments

def _run_single_match(args):
    candidate_path, replay_path, hero_seat = args
    sys.path.insert(0, os.path.dirname(candidate_path))
    
    # Load candidate dynamically
    mod_name = os.path.splitext(os.path.basename(candidate_path))[0]
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    candidate_mod = __import__(mod_name)
    
    with open(replay_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        act = candidate_mod.agent(obs)
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
            
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    return {
        "replay": os.path.basename(replay_path),
        "seat": hero_seat,
        "score": final_score
    }

def run_parallel_evaluation(candidate_path, match_list, max_workers=10):
    """
    Runs a list of matches in parallel with max_workers=10.
    match_list: list of tuples (replay_path, hero_seat)
    """
    tasks = [(candidate_path, r_path, seat) for r_path, seat in match_list]
    results = []
    t0 = time.time()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for res in executor.map(_run_single_match, tasks):
            results.append(res)
            
    elapsed = time.time() - t0
    scores = [r["score"] for r in results]
    mean_score = sum(scores) / len(scores) if scores else 0
    return {
        "candidate": os.path.basename(candidate_path),
        "matches": len(results),
        "mean_score": mean_score,
        "scores": scores,
        "results": results,
        "elapsed_seconds": elapsed
    }

if __name__ == "__main__":
    test_replays = [
        (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\91697084\episode-91697084-replay.json", 0),
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 1),
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 1),
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 1),
    ]
    cand = r"D:\kaggriculture\submission_rc5_c1_day_gate.py"
    print(f"Testing 10-worker parallel evaluation runner on {len(test_replays)} matches...")
    summary = run_parallel_evaluation(cand, test_replays, max_workers=10)
    print(f"Completed {summary['matches']} matches in {summary['elapsed_seconds']:.2f}s!")
    print(f"Mean Score: ${summary['mean_score']:,.0f}")
    for r in summary["results"]:
        print(f"  {r['replay']} (Seat {r['seat']}): ${r['score']:,.0f}")
