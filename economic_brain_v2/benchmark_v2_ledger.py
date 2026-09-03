import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments, json, os
import candidates.submission_adaptive_v2_economic as v2

def run_match_audit(replay_file, cand_seat):
    with open(replay_file) as f: rep = json.load(f)
    info = rep.get("info", {})
    seed = info.get("seed")
    opp_seat = 1 - cand_seat
    opp_actions = [frame[opp_seat].get("action") for frame in rep["steps"][1:]]
    live_hero = rep["rewards"][cand_seat]
    live_opp = rep["rewards"][opp_seat]
    
    # Reset match ledger
    for k in v2._MATCH_LEDGER:
        v2._MATCH_LEDGER[k] = 0
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    animal_deaths = 0
    prev_animals = 0
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs = env.state[cand_seat].observation
        act = v2.agent(obs)
        
        # Check animal deaths
        farm = obs.get("farms", [{}, {}])[cand_seat]
        curr_animals = 0
        for r in farm.get("tiles", []):
            for t in r:
                if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"):
                    curr_animals += 1
        
        actions = [None, None]
        actions[cand_seat] = act
        actions[opp_seat] = opp_actions[s]
        env.step(actions)
        
        # Check post-step animal count
        post_farm = env.state[cand_seat].observation.get("farms", [{}, {}])[cand_seat]
        post_animals = 0
        for r in post_farm.get("tiles", []):
            for t in r:
                if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP"):
                    post_animals += 1
        if post_animals < curr_animals:
            animal_deaths += (curr_animals - post_animals)

    v2._MATCH_LEDGER["animal_deaths"] = animal_deaths
    fin_hero = env.state[cand_seat].reward
    fin_opp = env.state[opp_seat].reward
    
    return os.path.basename(replay_file), live_hero, live_opp, fin_hero, fin_opp, dict(v2._MATCH_LEDGER)

def main():
    print("=========================================================================================")
    print("     BENCHMARKING V2 ADAPTIVE ECONOMIC AGENT ACROSS 5 LIVE LOSS GAUNTLETS                ")
    print("=========================================================================================")
    
    targets = [
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104475527-replay.json", 0), # RicardoLopez ($29.7k live)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104424149-replay.json", 0), # JZ ($64.2k live)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json", 0), # ayman ($75.0k live)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104388418-replay.json", 0), # Soumi ($30.1k live)
        (r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json", 0), # arao ($40.6k live)
    ]
    
    for rep_file, cand_seat in targets:
        name, live_h, live_o, fin_h, fin_o, ledger = run_match_audit(rep_file, cand_seat)
        print(f"\n--- Replay: {name} ---")
        print(f"  Live Recorded Tape : Hero ${live_h:,.0f} vs Opp ${live_o:,.0f} (Margin: ${live_h - live_o:+,.0f})")
        print(f"  V2 Economic Agent  : Hero ${fin_h:,.0f} vs Opp ${fin_o:,.0f} (Margin: ${fin_h - fin_o:+,.0f})")
        print(f"  Cash Lift over Live: ${fin_h - live_h:+,.0f}")
        print("  Financial Ledger:")
        print(f"    - Fertilizer Revenue : ${ledger['fertilizer_revenue']:,.0f}")
        print(f"    - Milk Revenue       : ${ledger['milk_revenue']:,.0f}")
        print(f"    - Wool Revenue       : ${ledger['wool_revenue']:,.0f}")
        print(f"    - Surplus Wheat Sold : {ledger['wheat_sold']} units")
        print(f"    - Wheat Seed Cost    : ${ledger['wheat_seed_cost']:,.0f}")
        print(f"    - Market Wheat Cost  : ${ledger['market_wheat_cost']:,.0f} (vs $41k in old bot!)")
        print(f"    - Worker Wages       : ${ledger['worker_wages']:,.0f}")
        print(f"    - Land Spend         : ${ledger['land_spend']:,.0f}")
        print(f"    - Animal Deaths      : {ledger['animal_deaths']} (Target: 0)")

if __name__ == "__main__":
    main()
