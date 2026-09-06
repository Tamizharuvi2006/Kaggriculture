import sys
sys.path.insert(0, r"D:\kaggriculture")

import os, json
import kaggle_environments
import submission_rc2_terminal_horizon as rc2_mod

# Compare:
# 1. Worst Floor: Soumi Ghosh Seat 1 (replay: episode-104388418-replay.json)
# 2. High Ceiling: 628M Seat 1 (seed: 628719714)

def trace_full_game(replay_file=None, seed=None, seat=1):
    if replay_file:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", replay_file)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - seat].get("action") for frame in steps[1:]]
    else:
        steps = range(721)
        opp_actions = None
        
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    daily_stats = {}
    prev_day = -1
    
    for step in range(len(steps) - 1):
        if env.done: break
        obs = env.state[seat].observation
        day = obs.day
        hour = obs.hour
        
        if day != prev_day:
            prev_day = day
            f = obs.farms[seat]
            priv = env.state[seat].observation.private
            shed = priv.get("shed", {})
            mkt = obs.market
            
            cows = 0
            sheep = 0
            straws = 0
            for r in range(len(f.tiles)):
                for c in range(len(f.tiles[r])):
                    t = f.tiles[r][c]
                    if isinstance(t, dict):
                        if t.get("animal") == "COW": cows += 1
                        elif t.get("animal") == "SHEEP": sheep += 1
                        elif t.get("crop") == "STRAWBERRY": straws += 1
                        
            daily_stats[day] = {
                "day": day,
                "money": f.money,
                "cows": cows,
                "sheep": sheep,
                "straw_tiles": straws,
                "shed_milk": shed.get("MILK", 0),
                "shed_straw": shed.get("STRAWBERRY", 0),
                "shed_wheat": shed.get("WHEAT", 0),
                "p_milk": mkt.prices.get("MILK", 0),
                "p_straw": mkt.prices.get("STRAWBERRY", 0),
                "inv_milk": mkt.inventory.get("MILK", 0),
                "inv_straw": mkt.inventory.get("STRAWBERRY", 0),
            }
            
        if replay_file:
            act0 = opp_actions[step] if seat == 1 else rc2_mod.agent(env.state[0].observation)
            act1 = rc2_mod.agent(env.state[1].observation) if seat == 1 else opp_actions[step]
        else:
            act0 = rc2_mod.agent(env.state[0].observation)
            act1 = rc2_mod.agent(env.state[1].observation)
            
        env.step([act0, act1])
        
    final_f = env.state[seat].observation.farms[seat]
    daily_stats[30] = {"day": 30, "money": final_f.money}
    return daily_stats

print("Tracing Worst Floor (Soumi Ghosh Seat 1)...")
worst_trace = trace_full_game(replay_file="episode-104388418-replay.json", seat=1)

print("Tracing High Ceiling (Seed 628719714 Seat 1)...")
high_trace = trace_full_game(seed=628719714, seat=1)

print("\n" + "=" * 115)
print(f"{'DAY':<4} | {'WORST MONEY':>12} | {'HIGH MONEY':>12} | {'WORST P_STR':>12} | {'HIGH P_STR':>12} | {'WORST INV_STR':>14} | {'HIGH INV_STR':>14} | {'W_COWS':>7} | {'H_COWS':>7}")
print("-" * 115)

for d in range(0, 31, 2):
    w = worst_trace.get(d, {})
    h = high_trace.get(d, {})
    print(f"D{d:02d}  | ${w.get('money', 0):>10,.0f} | ${h.get('money', 0):>10,.0f} | ${w.get('p_straw', 0):>10.1f} | ${h.get('p_straw', 0):>10.1f} | {w.get('inv_straw', 0):>14,} | {h.get('inv_straw', 0):>14,} | {w.get('cows', 0):>7} | {h.get('cows', 0):>7}")
