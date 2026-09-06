import urllib.request, json, os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
headers = {"User-Agent": "Mozilla/5.0"}
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH) as f:
        headers["Authorization"] = f"Bearer {f.read().strip()}"

for ep_id in [105105439, 105122067, 105120317]:
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Ep {ep_id} keys:", list(data.keys()))
            if "replay" in data:
                print(f"  Replay length: {len(data['replay'])}")
            if "episode" in data:
                ep = data["episode"]
                print(f"  Episode keys: {list(ep.keys())}")
                if "replayUrl" in ep:
                    print(f"  Replay URL: {ep['replayUrl']}")
    except Exception as e:
        print(f"Error on {ep_id}: {e}")
