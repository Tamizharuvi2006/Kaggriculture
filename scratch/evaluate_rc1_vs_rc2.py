import sys
sys.path.insert(0, r"D:\kaggriculture")

import importlib, json, os, time, kaggle_environments

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

def run_agent_eval(agent_module_name, label):
    mod = importlib.import_module(agent_module_name)
    scores = {}
    print(f"\n--- Running Evaluation: {label} ({agent_module_name}) ---")
    
    for r_name, cand_seat, opp_name in replays:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
        
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
        env.reset()
        
        for s in range(len(opp_actions)):
            if env.done: break
            obs = env.state[cand_seat].observation
            act = mod.agent(obs)
            joint = [None, None]
            joint[cand_seat] = act
            joint[1 - cand_seat] = opp_actions[s]
            env.step(joint)
            
        score = env.state[cand_seat].reward
        scores[opp_name] = score
        print(f"  {opp_name:<26}: ${score:,.0f}")
        sys.stdout.flush()
        
    total = sum(scores.values())
    avg = total / len(scores)
    print(f"  => TOTAL: ${total:,.0f} | AVG: ${avg:,.0f}")
    return scores, total, avg

print("=" * 95)
print("     OFFICIAL HEAD-TO-HEAD BENCHMARK: RC1 vs RC2 TERMINAL HORIZON     ")
print("=" * 95)

rc1_scores, rc1_total, rc1_avg = run_agent_eval("submission_rc1_ev_dispatcher", "RC1 Baseline")
rc2_scores, rc2_total, rc2_avg = run_agent_eval("submission_rc2_terminal_horizon", "RC2 Terminal Horizon")

print("\n" + "=" * 95)
print("     COMPARATIVE HEAD-TO-HEAD LEADERBOARD     ")
print("=" * 95)
print(f"  {'Opponent / Seed':<26} | {'RC1 Baseline':>12} | {'RC2 Horizon':>12} | {'Net Lift':>12}")
print("-" * 95)
for _, _, opp_name in replays:
    s1 = rc1_scores[opp_name]
    s2 = rc2_scores[opp_name]
    lift = s2 - s1
    print(f"  {opp_name:<26} | ${s1:>10,.0f} | ${s2:>10,.0f} | ${lift:>+10,.0f}")
print("-" * 95)
total_lift = rc2_total - rc1_total
print(f"  {'TOTAL AGGREGATE':<26} | ${rc1_total:>10,.0f} | ${rc2_total:>10,.0f} | ${total_lift:>+10,.0f}")
print(f"  {'AVERAGE PER MATCH':<26} | ${rc1_avg:>10,.0f} | ${rc2_avg:>10,.0f} | ${rc2_avg - rc1_avg:>+10,.0f}")
print("=" * 95)
