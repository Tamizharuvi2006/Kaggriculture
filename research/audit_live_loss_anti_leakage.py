import json
import os
import glob

def run_live_loss_audit():
    # 1. Load the 30 APEX 3.5 live losses
    json_path = r"D:\Kaggriculture\reports\live_match_telemetry\submission_55483322_episodes.json"
    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        
    episodes = d.get('episodes', [])
    recent_losses = []
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
                if our_rew < opp_rew:
                    recent_losses.append({
                        'episode_id': ep.get('id'),
                        'create_time': ep.get('createTime'),
                        'seat': seat,
                        'our_reward': our_rew,
                        'opp_reward': opp_rew,
                        'margin': our_rew - opp_rew,
                        'opp_sub_id': opp_agent.get('submissionId'),
                        'opp_score': opp_agent.get('initialScore', 0.0),
                        'our_score': our_agent.get('initialScore', 0.0)
                    })
                    
    # 2. Check for overlap with original 46 loss seeds / historical corpora
    corpus_path = r"D:\Kaggriculture\reports\APEX4_LOSS2POLICY_CORPUS.json"
    known_seeds = set()
    if os.path.exists(corpus_path):
        with open(corpus_path, "r", encoding="utf-8") as f:
            cdata = json.load(f)
            
    # Check against files in l++reviews and l+reviews
    historical_episodes = set()
    for f in glob.glob(r"D:\Kaggriculture\l++reviews\**\*.json", recursive=True):
        bname = os.path.basename(f).split("-")[0].replace(".json", "")
        if bname.isdigit():
            historical_episodes.add(int(bname))
    for f in glob.glob(r"D:\Kaggriculture\l+reviews\**\*.json", recursive=True):
        bname = os.path.basename(f).split("-")[0].replace(".json", "")
        if bname.isdigit():
            historical_episodes.add(int(bname))
            
    print(f"Total historical review episode IDs loaded: {len(historical_episodes)}")
    
    # Classify into KNOWN vs TRULY NEW
    classified_losses = []
    known_count = 0
    truly_new_count = 0
    
    for l in recent_losses:
        epid = l['episode_id']
        is_known = epid in historical_episodes
        if is_known:
            known_count += 1
            l['status_type'] = 'KNOWN'
        else:
            truly_new_count += 1
            l['status_type'] = 'TRULY_NEW'
        classified_losses.append(l)
        
    print(f"Total Recent Losses: {len(recent_losses)}")
    print(f"Known from prior corpora: {known_count}")
    print(f"TRULY NEW live losses: {truly_new_count}\n")
    
    return classified_losses

if __name__ == "__main__":
    run_live_loss_audit()
