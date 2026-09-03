import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, time, kaggle_environments
import submission_v4_1_clean as clean

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

def run_eval(replay_file, cand_seat, name):
    with open(replay_file) as f: rep = json.load(f)
    seed = rep["info"]["seed"]
    steps = rep["steps"]
    opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
    
    clean._MATCH_LEDGER = {
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
    
    t0 = time.time()
    for s in range(len(opp_actions)):
        if env.done: break
        obs = env.state[cand_seat].observation
        
        # Track animal deaths
        farm = obs["farms"][cand_seat]
        for row in farm["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("animal") and t.get("consecutive_unfed", 0) >= 2:
                    clean._MATCH_LEDGER["animal_deaths"] += 1
                    
        act = clean.agent(obs)
        joint = [None, None]
        joint[cand_seat] = act
        joint[1 - cand_seat] = opp_actions[s]
        env.step(joint)
        
    duration = time.time() - t0
    hero_score = env.state[cand_seat].reward
    opp_score = env.state[1 - cand_seat].reward
    live_hero = rep["rewards"][cand_seat]
    
    return {
        "name": name,
        "hero_score": hero_score,
        "opp_score": opp_score,
        "live_hero": live_hero,
        "ledger": clean._MATCH_LEDGER,
        "duration": duration,
    }

print("=" * 95)
print("     BENCHMARKING PURE CLEAN V4.1 (795 Lines, ZERO Legacy Machinery)            ")
print("=" * 95)

results = []
for r_name, seat, opp_name in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    res = run_eval(path, seat, opp_name)
    results.append(res)
    l = res["ledger"]
    diff = res["hero_score"] - res["live_hero"]
    print(f"--- {res['name']} ({res['duration']:.1f}s) ---")
    print(f"  Live Tape : ${res['live_hero']:,.0f}")
    print(f"  Clean V4.1: ${res['hero_score']:,.0f} vs Opp ${res['opp_score']:,.0f} (Lift: ${diff:+,.0f})")
    print(f"  Ledger    : Milk ${l['milk_revenue']:,.0f} | Wool ${l['wool_revenue']:,.0f} | Fert ${l['fertilizer_revenue']:,.0f}")
    print(f"              Market Feed: ${l['market_wheat_cost']:,.0f} | Animal Deaths: {l['animal_deaths']}")
    sys.stdout.flush()

print("\n" + "=" * 95)
total_live = sum(r["live_hero"] for r in results)
total_clean = sum(r["hero_score"] for r in results)
print(f"   Live Total Tape: ${total_live:,.0f} (Avg: ${total_live/5:,.0f})")
print(f"   Clean V4.1 Total: ${total_clean:,.0f} (Avg: ${total_clean/5:,.0f})")
print(f"   Aggregate Lift  : ${total_clean - total_live:+,.0f}")
print("=" * 95)
