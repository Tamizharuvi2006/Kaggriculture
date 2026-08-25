import json
import os
import glob

def analyze_losses():
    json_path = r"D:\Kaggriculture\reports\live_match_telemetry\submission_55483322_episodes.json"
    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        
    episodes = d.get('episodes', [])
    print(f"Total episodes in telemetry: {len(episodes)}")
    
    losses = []
    wins = []
    for ep in episodes:
        agents = ep.get('agents', [])
        if len(agents) == 2:
            a0, a1 = agents[0], agents[1]
            our_agent = a0 if a0.get('submissionId') == 55483322 else (a1 if a1.get('submissionId') == 55483322 else None)
            opp_agent = a1 if a0.get('submissionId') == 55483322 else (a0 if a1.get('submissionId') == 55483322 else None)
            if our_agent and opp_agent:
                our_rew = our_agent.get('reward', 0)
                opp_rew = opp_agent.get('reward', 0)
                seat = 0 if our_agent == a0 else 1
                item = {
                    'episode_id': ep.get('id'),
                    'create_time': ep.get('createTime'),
                    'seat': seat,
                    'our_reward': our_rew,
                    'opp_reward': opp_rew,
                    'margin': our_rew - opp_rew,
                    'opp_sub_id': opp_agent.get('submissionId'),
                    'opp_score': opp_agent.get('initialScore', 0.0),
                    'our_score': our_agent.get('initialScore', 0.0)
                }
                if our_rew < opp_rew:
                    losses.append(item)
                else:
                    wins.append(item)
                    
    print(f"Total Matches: {len(wins) + len(losses)} | Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%\n")
    
    for i, l in enumerate(losses):
        print(f"Loss {i+1:02d}: Ep {l['episode_id']} | Seat {l['seat']} | Score: ${l['our_reward']:,.0f} vs ${l['opp_reward']:,.0f} (Margin: -${abs(l['margin']):,.0f}) | Opp: {l['opp_sub_id']} ({l['opp_score']:.1f}) | {l['create_time'][:16]}")
        
    return losses, wins

if __name__ == "__main__":
    analyze_losses()
