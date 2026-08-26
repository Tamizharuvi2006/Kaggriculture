"""Test fetching full replay steps from Kaggle endpoints for episode 91581663."""
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

ep_id = 91581663

endpoints = [
    ("v1 episodes endpoint", f"https://www.kaggle.com/api/v1/episodes/{ep_id}", "GET", None),
    ("i EpisodeService/GetEpisode", f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}", "GET", None),
    ("i EpisodeService/ShowEpisode", "https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode", "POST", {"episodeId": int(ep_id)}),
    ("i EpisodeService/GetReplay", f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetReplay?episodeId={ep_id}", "GET", None),
    ("kaggle public cdn", f"https://www.kaggle.com/episodes/{ep_id}.json", "GET", None),
]

for name, url, method, payload in endpoints:
    print(f"\nTesting {name}: {url}")
    try:
        if method == "POST":
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method="GET")

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  -> SUCCESS! Keys: {list(data.keys())}")
            if "steps" in data:
                print(f"     FOUND FULL STEPS! Total steps: {len(data['steps'])}")
            elif "episode" in data:
                print(f"     Episode keys: {list(data['episode'].keys())}")
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"  -> Error: {e}")
