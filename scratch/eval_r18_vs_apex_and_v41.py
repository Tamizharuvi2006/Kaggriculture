import os
import sys
import json
import time
import numpy as np
import concurrent.futures
import kaggle_environments

sys.path.insert(0, r"D:\kaggriculture")
sys.path.insert(0, r"D:\kaggriculture\APEX35_ROLLBACK_ARCHIVE")

# The 20 authoritative tournament seeds
TOURNAMENT_SEEDS = [
    953494806, 711226357, 1624303674, 1362511072, 529528835,
    198057751, 2088147978, 805234002, 1262472034, 1802332305,
    1396349514, 2038933214, 1098481434, 1294246960, 114674719,
    1097619213, 1024364491, 1026490656, 1729007684, 1845173322
]

def _run_head_to_head_game(args):
    agent0_key, agent1_key, seed, match_idx = args
    import submission_rc18
    import submission_apex35_prod_backup
    import submission_v4_1_clean

    agent_map = {
        "rc18": submission_rc18.agent,
        "apex35": submission_apex35_prod_backup.agent,
        "v41": submission_v4_1_clean.agent,
    }

    p0_func = agent_map[agent0_key]
    p1_func = agent_map[agent1_key]

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()

    for s in range(720):
        if env.done:
            break
        obs0 = env.state[0].observation
        obs1 = env.state[1].observation
        try:
            act0 = p0_func(obs0)
        except Exception:
            act0 = {}
        try:
            act1 = p1_func(obs1)
        except Exception:
            act1 = {}
        env.step([act0, act1])

    score0 = int(env.state[0].observation["farms"][0]["money"])
    score1 = int(env.state[1].observation["farms"][1]["money"])

    return {
        "match_idx": match_idx,
        "seed": seed,
        "p0_name": agent0_key,
        "p1_name": agent1_key,
        "score0": score0,
        "score1": score1,
    }

def run_tournament(opponent_name, opp_key, num_seeds=10):
    print(f"\n" + "="*80)
    print(f"--- HEAD-TO-HEAD BATTLE: RC18 vs {opponent_name} (10 WORKERS, {num_seeds} SEEDS, SEAT SWAP) ---")
    print("="*80)

    seeds = TOURNAMENT_SEEDS[:num_seeds]
    tasks = []
    # Both seat orders for each seed
    for idx, seed in enumerate(seeds):
        # Seat 0: RC18, Seat 1: Opponent
        tasks.append(("rc18", opp_key, seed, f"Seed_{idx+1}_RC18_Seat0"))
        # Seat 0: Opponent, Seat 1: RC18
        tasks.append((opp_key, "rc18", seed, f"Seed_{idx+1}_RC18_Seat1"))

    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_run_head_to_head_game, tasks))
    elapsed = time.time() - t0

    rc18_scores = []
    opp_scores = []
    wins = 0
    ties = 0
    losses = 0

    print(f"{'Match':<22} | {'RC18 Seat':<10} | {'RC18 Score':>12} | {opponent_name + ' Score':>14} | {'Delta':>12} | {'Result':<6}")
    print("-" * 88)

    for r in results:
        is_rc18_seat0 = (r["p0_name"] == "rc18")
        if is_rc18_seat0:
            s_rc18 = r["score0"]
            s_opp = r["score1"]
            seat_str = "Seat 0"
        else:
            s_rc18 = r["score1"]
            s_opp = r["score0"]
            seat_str = "Seat 1"

        rc18_scores.append(s_rc18)
        opp_scores.append(s_opp)
        delta = s_rc18 - s_opp

        if s_rc18 > s_opp:
            res = "WIN"
            wins += 1
        elif s_rc18 < s_opp:
            res = "LOSS"
            losses += 1
        else:
            res = "TIE"
            ties += 1

        print(f"{r['match_idx']:<22} | {seat_str:<10} | ${s_rc18:>11,d} | ${s_opp:>13,d} | ${delta:>+11,d} | {res:<6}")

    total_matches = len(results)
    win_rate = (wins / total_matches) * 100.0
    mean_rc18 = float(np.mean(rc18_scores))
    mean_opp = float(np.mean(opp_scores))
    mean_delta = mean_rc18 - mean_opp

    print("=" * 88)
    print(f"RESULTS SUMMARY: RC18 vs {opponent_name} ({total_matches} matches in {elapsed:.1f}s)")
    print(f"  RC18 Record  : {wins} Wins / {ties} Ties / {losses} Losses  --> Win Rate: {win_rate:.1f}%")
    print(f"  RC18 Wealth  : Mean ${mean_rc18:,.0f} | Floor ${min(rc18_scores):,d} | Ceiling ${max(rc18_scores):,d}")
    print(f"  {opponent_name:<12}: Mean ${mean_opp:,.0f} | Floor ${min(opp_scores):,d} | Ceiling ${max(opp_scores):,d}")
    print(f"  Mean Delta   : ${mean_delta:+,.0f} per match ({'RC18 Advantage' if mean_delta > 0 else 'Opponent Advantage'})")
    print("=" * 88)

    return {
        "opponent": opponent_name,
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "win_rate": win_rate,
        "rc18_mean": mean_rc18,
        "rc18_floor": min(rc18_scores),
        "rc18_ceiling": max(rc18_scores),
        "opp_mean": mean_opp,
        "opp_floor": min(opp_scores),
        "opp_ceiling": max(opp_scores),
        "mean_delta": mean_delta,
        "elapsed_sec": elapsed,
        "matches": results,
    }

if __name__ == "__main__":
    print("Starting Head-to-Head Tournament Evaluation with 10 Parallel Workers...")
    res_apex = run_tournament("APEX 3.5", "apex35", num_seeds=10)
    res_v41 = run_tournament("V4.1 Clean", "v41", num_seeds=10)

    print("\n\n" + "#"*80)
    print("                      OVERALL HEAD-TO-HEAD SUMMARY TABLE")
    print("#"*80)
    print(f"{'Opponent':<15} | {'Record (W/T/L)':<16} | {'Win Rate':<10} | {'RC18 Mean':>12} | {'Opp Mean':>12} | {'Mean Delta':>12}")
    print("-" * 88)
    for res in [res_apex, res_v41]:
        rec = f"{res['wins']}W / {res['ties']}T / {res['losses']}L"
        print(f"{res['opponent']:<15} | {rec:<16} | {res['win_rate']:>8.1f}% | ${res['rc18_mean']:>11,.0f} | ${res['opp_mean']:>11,.0f} | ${res['mean_delta']:>+11,.0f}")
    print("#"*80)
