"""Test Kaggle API payload parameters for EpisodeService and LeaderboardService."""
import os
import json
import urllib.request
import urllib.error

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

payloads = [
    ("ListEpisodes with submissionId", "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes", {"submissionId": 55780289}),
    ("ListEpisodes with teamId", "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes", {"teamId": 16714457}),
    ("ListEpisodes with competitionId", "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes", {"competitionId": 99763}),
    ("ListEpisodes with competitionName", "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes", {"competitionName": "kaggriculture"}),
    ("GetLeaderboard with competitionName", "https://www.kaggle.com/api/i/competitions.LeaderboardService/GetLeaderboard", {"competitionName": "kaggriculture"}),
    ("GetTeam with teamId", "https://www.kaggle.com/api/i/competitions.TeamService/GetTeam", {"teamId": 16714457}),
    ("ListTeamMembers", "https://www.kaggle.com/api/i/competitions.TeamService/ListTeamMembers", {"teamId": 16714457}),
    ("ShowEpisode with episodeId", "https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId=99869827", None),
]

for name, url, payload in payloads:
    print(f"\nTesting: {name}")
    try:
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method="GET")

        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"  -> SUCCESS! Keys: {list(res.keys())}")
            if "episodes" in res:
                print(f"     Found {len(res['episodes'])} episodes")
            elif "teams" in res:
                print(f"     Found {len(res['teams'])} teams")
            elif "episode" in res:
                ep = res["episode"]
                print(f"     Episode agents: {len(ep.get('agents', []))}")
                for a in ep.get("agents", []):
                    print(f"       Agent subId={a.get('submissionId')}, teamId={a.get('teamId')}, score={a.get('initialScore')}")
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code}: {e.reason}")
        try:
            print("     Body:", e.read().decode("utf-8")[:200])
        except Exception:
            pass
    except Exception as e:
        print(f"  -> Error: {e}")
