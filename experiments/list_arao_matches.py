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
        print(f"Error listing episodes for {submission_id}: {e}")
        return None

res = list_episodes(55853587) # arao submission
if res and "episodes" in res:
    eps = res["episodes"]
    print(f"Total episodes played by arao (55853587): {len(eps)}")
    for ep in eps:
        ep_id = ep.get("id")
        agents = ep.get("agents", [])
        rewards = [a.get("reward") for a in agents]
        subs = [a.get("submissionId") for a in agents]
        elos = [a.get("initialScore") for a in agents]
        print(f"  Ep {ep_id} (Seed {ep.get('seed')}): Subs {subs} | Rewards: {rewards} | Elos: {elos}")
