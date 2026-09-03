import urllib.request
import json
import os

ep_id = 104379472
url = f"https://www.kaggle.com/episodes/{ep_id}.json"

print(f"Testing {url}...")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        print(f"SUCCESS! Downloaded {len(raw):,} bytes!")
        data = json.loads(raw.decode("utf-8"))
        print("Keys:", list(data.keys()))
        if "steps" in data:
            print(f"Found steps: {len(data['steps'])} steps!")
            save_path = r"D:\kaggriculture\reports\live_match_telemetry\episode_104379472_steps.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"Saved to {save_path}")
except Exception as e:
    print(f"Error: {e}")
