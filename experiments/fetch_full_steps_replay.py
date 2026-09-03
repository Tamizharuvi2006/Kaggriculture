import urllib.request
import json
import os

ep_id = 104379472
save_path = r"D:\kaggriculture\reports\live_match_telemetry\episode_104379472_full_steps.json"

urls = [
    f"https://storage.googleapis.com/kaggle-episodes/{ep_id}.json",
    f"https://www.kaggle.com/api/v1/episodes/{ep_id}.json",
    f"https://www.kaggle.com/api/v1/episodes/{ep_id}",
]

for url in urls:
    print(f"Trying {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(save_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp)
            print(f"Successfully downloaded full steps to {save_path} ({os.path.getsize(save_path):,} bytes)")
            break
    except Exception as e:
        print(f"Failed: {e}")
