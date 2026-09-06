import urllib.request, json, os

ep_id = 105198296
url = f"https://storage.googleapis.com/kaggle-episodes/{ep_id}.json"
save_path = f"reports/live_match_telemetry/episode-{ep_id}-replay.json"

print(f"Downloading replay for Episode {ep_id} from {url}...")
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

with open(save_path, "w", encoding="utf-8") as f:
    json.dump(data, f)

print(f"Successfully saved replay to {save_path} ({len(data.get('steps', []))} steps)")
