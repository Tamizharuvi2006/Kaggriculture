import json
import glob
import os

files = glob.glob(r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json")

print("=========================================================================================")
print(f"     FORENSIC AUDIT ACROSS ALL {len(files)} LIVE REPLAYS                                 ")
print("=========================================================================================")

for fpath in files:
    with open(fpath, "r", encoding="utf-8") as fp:
        replay = json.load(fp)
    
    info = replay.get("info", {})
    eid = info.get("EpisodeId")
    seed = info.get("seed")
    rewards = replay.get("rewards", [])
    agents = info.get("Agents", [])
    names = [a.get("Name") for a in agents]
    
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    hero_rew = rewards[hero_idx]
    opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    if not steps: continue
    
    # End-of-game shed
    final_frame = steps[-1]
    hero_obs = final_frame[hero_idx].get("observation", {})
    opp_obs = final_frame[opp_idx].get("observation", {})
    hero_shed = hero_obs.get("private", {}).get("shed", {})
    opp_shed = opp_obs.get("private", {}).get("shed", {})
    
    # Midgame prices (Day 15 and Day 25)
    p_d15 = steps[15*24][0].get("observation", {}).get("market", {}).get("prices", {}) if len(steps) > 15*24 else {}
    p_d25 = steps[25*24][0].get("observation", {}).get("market", {}).get("prices", {}) if len(steps) > 25*24 else {}
    
    delta = hero_rew - opp_rew
    status = "WIN" if delta > 0 else "LOSS"
    
    print(f"\nEpisode {eid} (Seed {seed}) | Result: {status} ({delta:+,.0f}) | Hero: ${hero_rew:,.0f} vs Opp: ${opp_rew:,.0f}")
    print(f"  Hero Final Shed Unsold: {hero_shed}")
    print(f"  Opp Final Shed Unsold: {opp_shed}")
    print(f"  D15 Prices: Milk ${p_d15.get('MILK')}, Wool ${p_d15.get('WOOL')}, Straw ${p_d15.get('STRAWBERRY')}")
    print(f"  D25 Prices: Milk ${p_d25.get('MILK')}, Wool ${p_d25.get('WOOL')}, Straw ${p_d25.get('STRAWBERRY')}")
