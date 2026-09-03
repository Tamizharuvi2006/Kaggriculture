import urllib.request
import json
import os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"

def get_headers():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            token = f.read().strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    return {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

def list_episodes(submission_id):
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(submission_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error listing episodes for {submission_id}: {e}")
        return None

# Check recent submissions
sub_ids = [55924297, 55924286, 55897281, 55867651, 55865375, 55780289]

for sid in sub_ids:
    print(f"\nChecking submission {sid}...")
    res = list_episodes(sid)
    if res and "episodes" in res:
        eps = res["episodes"]
        print(f"Found {len(eps)} episodes for submission {sid}")
        for ep in eps[:10]:
            ep_id = ep.get("id")
            agents = ep.get("agents", [])
            state = ep.get("state")
            names = [a.get("submission", {}).get("teamName", "") or a.get("submissionId") for a in agents]
            scores = [a.get("reward") for a in agents]
            elos = [a.get("initialScore") for a in agents]
            print(f"  Ep {ep_id}: {names} | Rewards: {scores} | Initial Elos: {elos} | State: {state}")
            if any("arao" in str(n).lower() for n in names):
                print(f"  >>> FOUND MATCH VS ARAO! Episode ID: {ep_id}")
