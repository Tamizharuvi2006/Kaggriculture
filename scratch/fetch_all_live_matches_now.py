import urllib.request
import json
import os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"

with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def list_episodes(submission_id):
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(submission_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error: {e}")
        return None

sub_ids = [55924297, 55924286]

all_losses = []

for sid in sub_ids:
    res = list_episodes(sid)
    if not res or "episodes" not in res:
        print(f"No data for {sid}")
        continue
    eps = res["episodes"]
    print(f"\n=========================================================================================")
    print(f"     SUBMISSION {sid}: {len(eps)} MATCHES TOTAL                                          ")
    print("=========================================================================================")
    
    wins = 0
    losses = 0
    ties = 0
    
    for ep in eps:
        ep_id = ep.get("id")
        agents = ep.get("agents", [])
        if len(agents) < 2:
            continue
        our_ag = next((a for a in agents if a.get("submissionId") == sid), None)
        opp_ag = next((a for a in agents if a.get("submissionId") != sid), None)
        if not our_ag or not opp_ag:
            continue
            
        our_rew = float(our_ag.get("reward") or 0.0)
        opp_rew = float(opp_ag.get("reward") or 0.0)
        our_elo = round(float(our_ag.get("initialScore") or 0.0), 1)
        opp_elo = round(float(opp_ag.get("initialScore") or 0.0), 1)
        opp_sub = opp_ag.get("submissionId")
        
        diff = our_rew - opp_rew
        if diff > 0:
            res_str = "WIN"
            wins += 1
        elif diff < 0:
            res_str = "LOSS"
            losses += 1
            all_losses.append({
                "sub_id": sid,
                "ep_id": ep_id,
                "our_rew": our_rew,
                "opp_rew": opp_rew,
                "our_elo": our_elo,
                "opp_elo": opp_elo,
                "opp_sub": opp_sub,
                "diff": diff
            })
        else:
            res_str = "TIE"
            ties += 1
            
        print(f"  Ep {ep_id}: vs Sub {opp_sub} (Elo {opp_elo}) | Us: ${our_rew:,.0f} vs Opp: ${opp_rew:,.0f} | Delta: {diff:+,.0f} | {res_str}")
        
    print(f"\nSummary for {sid}: {wins} W / {losses} L / {ties} T (Total: {len(eps)})")

print("\n\nAll Losses across submissions:")
for l in all_losses:
    print(l)
