import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments, json, os
import economic_brain_v2.submission_adaptive_v3_economic as v3

def run_match_audit(replay_file, cand_seat):
    with open(replay_file) as f: rep = json.load(f)
    info = rep.get("info", {})
    seed = info.get("seed")
    steps = rep["steps"]
    
    hero_seat = cand_seat
    opp_seat = 1 - cand_seat
    
    v3._MATCH_LEDGER = {
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
    
    opp_actions = [frame[opp_seat].get("action") for frame in steps[1:]]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
    env.reset()
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs = env.state[hero_seat].observation
        
        # Track animal deaths
        farm = obs["farms"][hero_seat]
        for row in farm["tiles"]:
            for t in row:
                if isinstance(t, dict) and t.get("animal") and t.get("consecutive_unfed", 0) >= 2:
                    v3._MATCH_LEDGER["animal_deaths"] += 1
                    
        act = v3.agent(obs)
        
        # Execute counterfactual step against recorded opponent actions
        joint = [None, None]
        joint[hero_seat] = act
        joint[opp_seat] = opp_actions[s]
        env.step(joint)
        
    v3_score = env.state[hero_seat].reward
    opp_score = env.state[opp_seat].reward
    return v3_score, opp_score, v3._MATCH_LEDGER, rep["rewards"][hero_seat], rep["rewards"][opp_seat]

replays = [
    ("episode-104475527-replay.json", 0), # RicardoLópez (1052 Elo)
    ("episode-104424149-replay.json", 0), # JZ (1000+ Elo)
    ("episode-104433117-replay.json", 0), # ayman elamin (1000+ Elo)
    ("episode-104388418-replay.json", 0), # Soumi Ghosh
    ("episode-104379472-replay.json", 0), # arao
]

print("=" * 89)
print("     BENCHMARKING V3 ADAPTIVE ECONOMIC AGENT ACROSS 5 LIVE LOSS GAUNTLETS        ")
print("=" * 89)

total_live = 0
total_v3 = 0

for r_name, seat in replays:
    path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
    v3_sc, opp_sc, ledger, live_hero, live_opp = run_match_audit(path, seat)
    diff = v3_sc - live_hero
    total_live += live_hero
    total_v3 += v3_sc
    
    print(f"\n--- Replay: {r_name} ---")
    print(f"  Live Recorded Tape : Hero ${live_hero:,.0f} vs Opp ${live_opp:,.0f} (Margin: ${live_hero - live_opp:+,.0f})")
    print(f"  V3 Economic Agent  : Hero ${v3_sc:,.0f} vs Opp ${opp_sc:,.0f} (Margin: ${v3_sc - opp_sc:+,.0f})")
    print(f"  Cash Lift over Live: ${diff:+,.0f}")
    print(f"  Financial Ledger:")
    print(f"    - Fertilizer Revenue : ${ledger['fertilizer_revenue']:,.0f}")
    print(f"    - Milk Revenue       : ${ledger['milk_revenue']:,.0f}")
    print(f"    - Wool Revenue       : ${ledger['wool_revenue']:,.0f}")
    print(f"    - Surplus Wheat Sold : {ledger['wheat_sold']} units")
    print(f"    - Wheat Seed Cost    : ${ledger['wheat_seed_cost']:,.0f}")
    print(f"    - Market Wheat Cost  : ${ledger['market_wheat_cost']:,.0f} (vs $41k in old bot!)")
    print(f"    - Worker Wages       : ${ledger['worker_wages']:,.0f}")
    print(f"    - Land Spend         : ${ledger['land_spend']:,.0f}")
    print(f"    - Animal Deaths      : {ledger['animal_deaths']} (Target: 0)")

print("\n" + "=" * 89)
print(f"   SUMMARY ACROSS ALL 5 MATCHES:")
print(f"   Live Total: ${total_live:,.0f} (Avg: ${total_live/5:,.0f})")
print(f"   V3 Total  : ${total_v3:,.0f} (Avg: ${total_v3/5:,.0f})")
print(f"   Net Lift  : ${total_v3 - total_live:+,.0f} (Avg Lift: ${(total_v3 - total_live)/5:+,.0f}/match)")
print("=" * 89)
