import json, os, sys
import urllib.request
from pathlib import Path

TOKEN_PATH = Path(r"C:\Users\aruvi\.kaggle\access_token")
token = TOKEN_PATH.read_text(encoding="utf-8").strip()

url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
payload = {"submissionId": 55992396}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "KaggricultureForensics/1.0"
    },
    method="POST"
)

with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

episodes = data.get("episodes", [])
print(f"Total episodes for RC4.2 (55992396): {len(episodes)}")
for ep in episodes:
    ep_id = ep.get("id")
    agents = ep.get("agents", [])
    # Find our hero agent and opponent agent
    hero = None
    opp = None
    for a in agents:
        if a.get("submissionId") == 55992396:
            hero = a
        else:
            opp = a
    hero_reward = hero.get("reward", 0) if hero else 0
    opp_reward = opp.get("reward", 0) if opp else 0
    opp_name = opp.get("submission", {}).get("teamName", "Unknown") if opp else "Unknown"
    opp_score = opp.get("updatedScore", 0) if opp else 0
    print(f"Episode {ep_id}: Hero=${hero_reward:,.0f} vs Opp ({opp_name})=${opp_reward:,.0f} (Opp Elo: {opp_score:.1f})")
