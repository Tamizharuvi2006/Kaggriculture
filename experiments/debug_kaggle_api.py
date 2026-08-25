"""Debug Kaggle EpisodeService API call."""
import os
import json
import urllib.request

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

ep_id = 91305315
url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}"
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("Success! Keys:", list(data.keys()))
        episode = data.get("episode", {})
        print("Seed:", episode.get("seed"))
        print("Episode keys:", list(episode.keys()))
except Exception as e:
    print(f"Error: {e}")
