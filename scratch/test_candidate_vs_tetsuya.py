import sys
sys.path.insert(0, r"D:\kaggriculture")

import json
import kaggle_environments
import submission_challenger_exp208_clean as challenger

def test_against_tetsuya(replay_path):
    with open(replay_path, "r", encoding="utf-8") as f:
        replay = json.load(f)
        
    info = replay.get("info", {})
    eid = info.get("EpisodeId")
    seed = info.get("seed")
    agents = info.get("Agents", [])
    rewards = replay.get("rewards", [])
    
    tet_idx = 0 if "tetsuya" in agents[0].get("Name", "").lower() else 1
    opp_idx = 1 - tet_idx
    tet_name = agents[tet_idx].get("Name")
    orig_opp_name = agents[opp_idx].get("Name")
    orig_tet_rew = rewards[tet_idx]
    orig_opp_rew = rewards[opp_idx]
    
    steps = replay.get("steps", [])
    tet_actions = [frame[tet_idx].get("action") for frame in steps[1:]]
    
    # Run simulation with Candidate in place of Opponent
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    challenger._V18_SELECTED_DAY = {0: None, 1: None}
    challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(tet_actions)):
        if env.done: break
        obs_candidate = env.state[opp_idx].observation
        act_candidate = challenger.agent(obs_candidate)
        act_tetsuya = tet_actions[s]
        
        actions = [None, None]
        actions[opp_idx] = act_candidate
        actions[tet_idx] = act_tetsuya
        env.step(actions)
        
    fin_candidate = env.state[opp_idx].reward
    fin_tetsuya = env.state[tet_idx].reward
    
    status = "WIN" if fin_candidate > fin_tetsuya else "LOSS"
    margin = fin_candidate - fin_tetsuya
    
    print(f"\nEpisode {eid} (Seed {seed}):")
    print(f"  Original Match  : {tet_name} ${orig_tet_rew:,.0f} vs {orig_opp_name} ${orig_opp_rew:,.0f} (Margin: {orig_opp_rew - orig_tet_rew:+,.0f})")
    print(f"  Candidate Match : {tet_name} ${fin_tetsuya:,.0f} vs Candidate ${fin_candidate:,.0f} ({status}, Margin: {margin:+,.0f})")
    return eid, fin_candidate, fin_tetsuya, margin, status

def main():
    print("=========================================================================================")
    print("     COUNTERFACTUAL LAB: CLEAN CANDIDATE VS TETSUYA'S EXACT RECORDED MOVES               ")
    print("=========================================================================================")
    
    replays = [
        r"D:\kaggriculture\topreply\win\104514177.json",
        r"D:\kaggriculture\topreply\win\104492175.json",
        r"D:\kaggriculture\topreply\win\103857429.json",
        r"D:\kaggriculture\topreply\loss\104499847.json",
    ]
    
    for r in replays:
        test_against_tetsuya(r)

if __name__ == "__main__":
    main()
