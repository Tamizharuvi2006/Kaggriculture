import sys
sys.path.insert(0, r"D:\kaggriculture")

import json
import kaggle_environments
import submission_challenger_exp208_clean as challenger

episodes = [
    ("104379472", "arao (943 Elo)"),
    ("104388418", "Soumi Ghosh (1011 Elo)"),
    ("104424149", "JZ (884 Elo)"),
    ("104433117", "ayman elamin (882 Elo)"),
    ("104475527", "RicardoLopez (982 Elo)")
]

challenger.STRATEGY["fixed_board_adaptation"] = True
challenger.STRATEGY["adaptive_animal_mode"] = "mirror"
challenger.STRATEGY["adaptive_capital_priority"] = False

print("=========================================================================================")
print("     PER-EPISODE PERFORMANCE WITH ADAPTATION ENABLED                                     ")
print("=========================================================================================")

for eid, opp_name in episodes:
    ep_file = rf"D:\kaggriculture\reports\live_match_telemetry\episode-{eid}-replay.json"
    with open(ep_file, "r", encoding="utf-8") as f:
        replay = json.load(f)
        
    seed = replay.get("info", {}).get("seed")
    rewards = replay.get("rewards", [])
    agents = replay.get("info", {}).get("Agents", [])
    hero_idx = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_idx = 1 - hero_idx
    orig_h = rewards[hero_idx]
    orig_o = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    opp_actions = [frame[opp_idx].get("action") for frame in steps[1:]]
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    challenger._V18_SELECTED_DAY = {0: None, 1: None}
    challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(opp_actions)):
        if env.done: break
        obs_hero = env.state[hero_idx].observation
        act_hero = challenger.agent(obs_hero)
        act_opp = opp_actions[s]
        
        actions = [None, None]
        actions[hero_idx] = act_hero
        actions[opp_idx] = act_opp
        env.step(actions)
        
    fin_h = env.state[hero_idx].reward
    fin_o = env.state[opp_idx].reward
    gain = fin_h - orig_h
    status = "WIN" if fin_h > fin_o else "LOSS"
    print(f"Ep {eid} vs {opp_name:23s}: Orig ${orig_h:,.0f} -> New ${fin_h:,.0f} (Gain: {gain:+8,.0f}) | Opp: ${fin_o:,.0f} ({status})")
