import sys
import os
import json
import urllib.request

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
OUTPUT_DIR = r"D:\kaggriculture\reports\live_match_telemetry"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

ep_id = 104379472
print(f"Fetching replay for Episode {ep_id} (vs arao 943 Elo)...")

urls = [
    f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}",
    f"https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode?episodeId={ep_id}",
    f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisodeReplay?episodeId={ep_id}",
]

ep_data = None
for url in urls:
    print(f"Trying GET {url}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ep_data = json.loads(resp.read().decode("utf-8"))
            print(f"Success with {url}!")
            break
    except Exception as e:
        print(f"Failed: {e}")

if not ep_data:
    # Try POST ShowEpisode with {"id": ...}
    print("Trying POST ShowEpisode with {'id': ep_id}...")
    req = urllib.request.Request(
        "https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode",
        data=json.dumps({"id": ep_id}).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ep_data = json.loads(resp.read().decode("utf-8"))
            print("Success with POST ShowEpisode!")
    except Exception as e:
        print(f"Failed POST: {e}")

if ep_data:
    save_path = os.path.join(OUTPUT_DIR, f"episode_{ep_id}_arao_loss.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(ep_data, f, indent=2)
    print(f"Saved replay to {save_path} ({os.path.getsize(save_path):,} bytes)")
else:
    print("Could not download replay.")
