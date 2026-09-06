import urllib.request, json, os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
headers = {"User-Agent": "Mozilla/5.0"}
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH) as f:
        headers["Authorization"] = f"Bearer {f.read().strip()}"

ep_ids = [105105439, 105107201, 105104584, 105112452, 105116829]

for ep_id in ep_ids:
    url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ep = data.get("episode", {})
            agents = ep.get("agents", [])
            rewards = [a.get("reward") for a in agents]
            sids = [a.get("submissionId") for a in agents]
            elos = [a.get("initialScore") for a in agents]
            seed = ep.get("seed")
            print(f"Ep {ep_id}: Seed={seed} | Rewards={rewards} | Sids={sids} | InitialElos={[round(e, 1) for e in elos if e]}")
    except Exception as e:
        print(f"Error on {ep_id}: {e}")
