import os, sys, json, time
import concurrent.futures
import numpy as np
import kaggle_environments

# List of 20 distinct diverse matches
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

def _run_single_match(args):
    candidate_path, replay_path, hero_seat = args
    sys.path.insert(0, os.path.dirname(candidate_path))
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
    return final_score

def run_paired_suite():
    cand_rc42 = r"D:\kaggriculture\submission_rc4_2_hybrid.py"
    cand_rc5c1 = r"D:\kaggriculture\submission_rc5_c1_day_gate.py"
    
    print(f"Executing 20-match paired evaluation (RC4.2 vs RC5-C1) across 10 parallel workers...")
    t0 = time.time()
    
    tasks_rc42 = [(cand_rc42, r_path, seat) for r_path, seat in SELECTED_REPLAYS]
    tasks_rc5c1 = [(cand_rc5c1, r_path, seat) for r_path, seat in SELECTED_REPLAYS]
    
    scores_rc42 = []
    scores_rc5c1 = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        for s in executor.map(_run_single_match, tasks_rc42):
            scores_rc42.append(s)
            
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        for s in executor.map(_run_single_match, tasks_rc5c1):
            scores_rc5c1.append(s)
            
    elapsed = time.time() - t0
    print(f"All 40 matches finished in {elapsed:.2f} seconds! (10 parallel workers)\n")
    
    deltas = np.array(scores_rc5c1) - np.array(scores_rc42)
    wins = int(np.sum(deltas > 0))
    losses = int(np.sum(deltas < 0))
    ties = int(np.sum(deltas == 0))
    
    # Bootstrap 95% Confidence Interval
    np.random.seed(42)
    boot_means = [np.mean(np.random.choice(deltas, size=len(deltas), replace=True)) for _ in range(10000)]
    ci_lower = np.percentile(boot_means, 2.5)
    ci_upper = np.percentile(boot_means, 97.5)
    
    print("=" * 95)
    print(f"{'MATCH':<5} | {'REPLAY ID':<20} | {'RC4.2 SCORE':<14} | {'RC5-C1 SCORE':<14} | {'DELTA':<12} | {'OUTCOME'}")
    print("-" * 95)
    for i, (r_path, seat) in enumerate(SELECTED_REPLAYS):
        s42 = scores_rc42[i]
        sc1 = scores_rc5c1[i]
        d = sc1 - s42
        r_name = os.path.basename(r_path)[:19]
        outcome = "WIN [GREEN]" if d > 0 else ("TIE [EQUAL]" if d == 0 else "LOSS [RED]")
        print(f"#{i+1:<4} | {r_name:<20} | ${s42:>11,} | ${sc1:>11,} | ${d:>+10,} | {outcome}")
    print("=" * 95)
    
    print("\n" + "=" * 60)
    print("PAIRED STATISTICAL SUMMARY (20 DIVERSE MATCHES):")
    print("=" * 60)
    print(f"  RC4.2 Mean:        ${np.mean(scores_rc42):>10,.0f}")
    print(f"  RC5-C1 Mean:       ${np.mean(scores_rc5c1):>10,.0f}  (DELTA: ${np.mean(deltas):>+10,.0f})")
    print(f"  RC4.2 Median:      ${np.median(scores_rc42):>10,.0f}")
    print(f"  RC5-C1 Median:     ${np.median(scores_rc5c1):>10,.0f}")
    print(f"  RC4.2 Floor (Min): ${np.min(scores_rc42):>10,.0f}")
    print(f"  RC5-C1 Floor (Min):${np.min(scores_rc5c1):>10,.0f}  (DELTA: ${np.min(scores_rc5c1)-np.min(scores_rc42):>+10,.0f})")
    print(f"  RC4.2 Ceiling:     ${np.max(scores_rc42):>10,.0f}")
    print(f"  RC5-C1 Ceiling:    ${np.max(scores_rc5c1):>10,.0f}")
    print(f"  Record:            {wins} Wins / {losses} Losses / {ties} Ties")
    print(f"  Win/Tie Rate:      {(wins+ties)/len(deltas)*100:.1f}%")
    print(f"  95% Bootstrap CI:  [${ci_lower:>+,.0f}, ${ci_upper:>+,.0f}]")
    print("=" * 60)
    
    # Worst losing match
    worst_idx = int(np.argmin(deltas))
    print(f"\nWORST REGRESSION INSPECTION:")
    print(f"  Match #{worst_idx+1}: {SELECTED_REPLAYS[worst_idx][0]}")
    print(f"  RC4.2: ${scores_rc42[worst_idx]:,}, RC5-C1: ${scores_rc5c1[worst_idx]:,} (Delta: ${deltas[worst_idx]:+,})")

if __name__ == "__main__":
    run_paired_suite()
