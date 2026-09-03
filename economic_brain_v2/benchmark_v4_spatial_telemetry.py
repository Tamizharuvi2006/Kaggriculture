import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, kaggle_environments
import economic_brain_v2.submission_adaptive_v4_spatial as v4

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

def run_v4_telemetry(replay_file, cand_seat, name):
    with open(replay_file) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
    
    v4._MATCH_LEDGER = {
        "fertilizer_revenue": 0.0,
        "milk_revenue": 0.0,
        "wool_revenue": 0.0,
        "wheat_sold": 0,
        "wheat_seed_cost": 0.0,
        "market_wheat_cost": 0.0,
        "worker_wages": 0.0,
        "land_spend": 0.0,
        "animal_deaths": 0,
    }
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
    env.reset()
    
    daily_stats = {}
    total_tasks_generated = 0
    total_tasks_executed = 0
    total_travel_turns = 0
    total_starved_tasks = 0
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs = env.state[cand_seat].observation
        day = s // 24
        hour = s % 24
        
        farm = obs["farms"][cand_seat]
        tiles = farm["tiles"]
        private = obs.get("private", {}) or {}
        shed = private.get("shed", {}) or {}
        
        # Track animal deaths
        for row in tiles:
            for t in row:
                if isinstance(t, dict) and t.get("animal") and t.get("consecutive_unfed", 0) >= 2:
                    v4._MATCH_LEDGER["animal_deaths"] += 1
        
        positions = [tuple(pos) for pos in farm.get("hands", [])]
        invs = private.get("inventories", [])
        tasks = v4._build_tasks(obs, positions, invs)
        total_tasks_generated += len(tasks)
        
        act = v4.agent(obs)
        hand_acts = act.get("hands", [])
        active_acts = 0
        travel_acts = 0
        for a in hand_acts:
            if a and len(a) > 0:
                if a[0] == "MOVE":
                    travel_acts += 1
                elif a[0] != "PASS":
                    active_acts += 1
                    
        total_tasks_executed += active_acts
        total_travel_turns += travel_acts
        if len(tasks) > len(hand_acts):
            total_starved_tasks += (len(tasks) - len(hand_acts))
            
        if hour == 0 and day in (0, 4, 8, 12, 16, 20, 24, 28):
            grazing = 0
            crops = {}
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("animal"): grazing += 1
                        if t.get("crop"): crops[t["crop"]] = crops.get(t["crop"], 0) + 1
            in_shed = int(shed.get("COW", 0)) + int(shed.get("SHEEP", 0))
            daily_stats[day] = {
                "cash": farm["money"],
                "hands": len(farm["hands"]),
                "grazing": grazing,
                "in_shed": in_shed,
                "wheat_shed": int(shed.get("WHEAT", 0)),
                "crops": crops,
            }
            
        joint = [None, None]
        joint[cand_seat] = act
        joint[1 - cand_seat] = opp_actions[s]
        env.step(joint)
        
    v4_score = env.state[cand_seat].reward
    opp_score = env.state[1 - cand_seat].reward
    live_hero = rep["rewards"][cand_seat]
    live_opp = rep["rewards"][1 - cand_seat]
    
    return {
        "name": name,
        "v4_score": v4_score,
        "opp_score": opp_score,
        "live_hero": live_hero,
        "live_opp": live_opp,
        "ledger": v4._MATCH_LEDGER,
        "daily": daily_stats,
        "tasks_generated": total_tasks_generated,
        "tasks_executed": total_tasks_executed,
        "travel_turns": total_travel_turns,
        "tasks_starved": total_starved_tasks,
    }

print("=" * 105)
print("     V4 SPATIAL LOCALITY DISPATCHER: MULTI-GAUNTLET TELEMETRY AUDIT             ")
print("=" * 105)

results = []
for r_name, seat, opp_name in replays:
    print(f"\nEvaluating {opp_name}...")
    sys.stdout.flush()
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    res = run_v4_telemetry(path, seat, opp_name)
    results.append(res)
    
    l = res["ledger"]
    diff = res["v4_score"] - res["live_hero"]
    exec_rate = (res["tasks_executed"] / max(1, res["tasks_generated"])) * 100
    print(f"--- Opponent: {res['name']} ---")
    print(f"  Live Tape : ${res['live_hero']:,.0f} vs Opp ${res['live_opp']:,.0f} (Margin: ${res['live_hero'] - res['live_opp']:+,.0f})")
    print(f"  V4 Agent  : ${res['v4_score']:,.0f} vs Opp ${res['opp_score']:,.0f} (Margin: ${res['v4_score'] - res['opp_score']:+,.0f})")
    print(f"  Lift over Live: ${diff:+,.0f}")
    print(f"  Physical Locality Metrics:")
    print(f"    - Tasks Generated : {res['tasks_generated']:,} | Direct Actions Executed: {res['tasks_executed']:,}")
    print(f"    - Travel Moves    : {res['travel_turns']:,}")
    print(f"    - Execution Ratio : {exec_rate:.1f}%")
    print(f"    - Tasks Starved   : {res['tasks_starved']:,}")
    print(f"  Financial Ledger:")
    print(f"    - Fertilizer Revenue : ${l['fertilizer_revenue']:,.0f}")
    print(f"    - Milk Revenue       : ${l['milk_revenue']:,.0f}")
    print(f"    - Wool Revenue       : ${l['wool_revenue']:,.0f}")
    print(f"    - Surplus Wheat Sold : {l['wheat_sold']} units")
    print(f"    - Market Wheat Cost  : ${l['market_wheat_cost']:,.0f}")
    print(f"    - Worker Wages       : ${l['worker_wages']:,.0f}")
    print(f"    - Animal Deaths      : {l['animal_deaths']}")
    print(f"  Bi-Daily Farm Telemetry:")
    for d, s in res["daily"].items():
        crp = " ".join(f"{c[:3]}:{n}" for c, n in s["crops"].items()) if s["crops"] else "-"
        print(f"    D{d:02d} | Cash: ${s['cash']:>7,.0f} | Hands: {s['hands']:>2} | Grazing: {s['grazing']:>2} | InShed: {s['in_shed']:>2} | WheatShed: {s['wheat_shed']:>2} | Crops: {crp}")
    sys.stdout.flush()



print("\n" + "=" * 105)
total_live = sum(r["live_hero"] for r in results)
total_v4 = sum(r["v4_score"] for r in results)
print(f"   5-MATCH OVERALL SCORE:")
print(f"   Live Total Tape: ${total_live:,.0f} (Avg: ${total_live/5:,.0f})")
print(f"   V4 Agent Total : ${total_v4:,.0f} (Avg: ${total_v4/5:,.0f})")
print(f"   Aggregate Lift : ${total_v4 - total_live:+,.0f} (Avg Lift: ${(total_v4 - total_live)/5:+,.0f}/match)")
print("=" * 105)
