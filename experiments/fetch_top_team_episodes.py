"""EXP074: Fetch and parse episodes for top 3000+ teams (Crop Dusta, Ryo Hasegawa, Subramanya N)."""
import os
import json
import urllib.request
import urllib.error

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
OUTPUT_DIR = os.path.join(r"D:\kaggriculture", "reports", "live_match_telemetry", "top_tier_replays")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

top_teams = [
    {"teamId": 16714457, "name": "Crop Dusta", "score": 3092.3},
    {"teamId": 16644287, "name": "Ryo Hasegawa", "score": 3038.8},
    {"teamId": 16705390, "name": "Subramanya N", "score": 2974.2},
    {"teamId": 16665224, "name": "tyz123456", "score": 2893.5},
    {"teamId": 16730065, "name": "Blu3s", "score": 2890.3},
]

def fetch_team_episodes(team_id: int):
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"teamId": int(team_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("episodes", [])
    except Exception as e:
        print(f"Error for team {team_id}: {e}")
        return []

for t in top_teams:
    print(f"\nFetching episodes for Rank Leader: {t['name']} (Score: {t['score']}, Team ID: {t['teamId']})...")
    eps = fetch_team_episodes(t["teamId"])
    print(f"  -> Retrieved {len(eps)} tournament matches!")
    if eps:
        # Save team match list
        out_f = os.path.join(OUTPUT_DIR, f"team_{t['teamId']}_{t['name'].replace(' ', '_')}_episodes.json")
        with open(out_f, "w", encoding="utf-8") as fp:
            json.dump({"team": t, "episodes": eps}, fp, indent=2)
        print(f"  -> Saved metadata to {out_f}")

        # Show recent 5 matches
        for ep in eps[:5]:
            agents = ep.get("agents", [])
            r0 = agents[0].get("reward") if len(agents) > 0 else "N/A"
            r1 = agents[1].get("reward") if len(agents) > 1 else "N/A"
            print(f"     Ep {ep.get('id')}: Rewards = [{r0}, {r1}]")
