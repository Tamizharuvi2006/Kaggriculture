import urllib.request
import json
import os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"

with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

ep_ids = [104379472, 104388418, 104424149, 104433117, 104475527]
out_dir = r"D:\kaggriculture\reports\live_match_telemetry\downloaded_losses"
os.makedirs(out_dir, exist_ok=True)

for eid in ep_ids:
    print(f"\nFetching episode {eid}...")
    
    # 1. First get metadata to get seed and agent positions
    meta_url = f"https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode?episodeId={eid}"
    meta = None
    try:
        req = urllib.request.Request(meta_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
            print(f"  Got metadata for {eid}: Seed = {meta.get('episode', {}).get('seed')}")
            with open(os.path.join(out_dir, f"meta_{eid}.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
    except Exception as e:
        print(f"  Meta error: {e}")
        
    # 2. Now check if GCS has the replay JSON
    gcs_url = f"https://storage.googleapis.com/kaggle-episodes/{eid}.json"
    try:
        req = urllib.request.Request(gcs_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            data = json.loads(raw.decode("utf-8"))
            print(f"  SUCCESS! Downloaded full replay {eid}: {len(raw):,} bytes, {len(data.get('steps', []))} steps")
            with open(os.path.join(out_dir, f"replay_{eid}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f)
    except Exception as e:
        print(f"  GCS error: {e}")
