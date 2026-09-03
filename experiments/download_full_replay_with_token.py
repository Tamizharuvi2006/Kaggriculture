import sys
import os
import json
import urllib.request
import urllib.parse
import base64

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
KAGGLE_JSON = r"C:\Users\aruvi\.kaggle\kaggle.json"
OUTPUT_DIR = r"D:\kaggriculture\reports\live_match_telemetry"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ep_id = 104379472

print("=========================================================================================")
print(f"     FETCHING FULL REPLAY FOR EPISODE {ep_id} VIA KAGGLE AUTH                           ")
print("=========================================================================================")

headers_list = []

# 1. Bearer token from access_token
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        tok = f.read().strip()
    headers_list.append({
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    })

# 2. Basic auth from kaggle.json
if os.path.exists(KAGGLE_JSON):
    with open(KAGGLE_JSON, "r", encoding="utf-8") as f:
        kj = json.load(f)
    username = kj.get("username", "")
    key = kj.get("key", "")
    basic_auth = base64.b64encode(f"{username}:{key}".encode("utf-8")).decode("utf-8")
    headers_list.append({
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    })

# Endpoints to test
endpoints = [
    ("POST", "https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisodeReplay", {"episodeId": ep_id}),
    ("POST", "https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode", {"id": ep_id}),
    ("POST", "https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode", {"episodeId": ep_id}),
    ("GET", f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={ep_id}", None),
    ("GET", f"https://www.kaggle.com/api/v1/episodes/{ep_id}", None),
    ("GET", f"https://www.kaggle.com/api/v1/competitions/episodes/{ep_id}", None),
    ("GET", f"https://storage.googleapis.com/kaggle-episodes/{ep_id}.json", None),
]

replay_data = None

for method, url, body in endpoints:
    for headers in headers_list:
        print(f"Testing {method} {url}...")
        try:
            if method == "POST":
                data = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            else:
                req = urllib.request.Request(url, headers=headers, method="GET")
                
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                parsed = json.loads(raw.decode("utf-8"))
                # Check if it contains steps or replay
                if "steps" in parsed or "replay" in parsed or "actions" in parsed or "episode" in parsed:
                    print(f"  --> SUCCESS! Keys: {list(parsed.keys())[:5]}, size: {len(raw):,} bytes")
                    replay_data = parsed
                    save_path = os.path.join(OUTPUT_DIR, f"episode_{ep_id}_complete_replay.json")
                    with open(save_path, "w", encoding="utf-8") as fp:
                        json.dump(parsed, fp, indent=2)
                    print(f"Saved complete replay to {save_path}")
                    break
        except Exception as e:
            print(f"  Failed: {e}")
    if replay_data and ("steps" in replay_data or "replay" in replay_data):
        break

if not replay_data:
    print("\nCould not retrieve replay with standard endpoints.")
