import urllib.request
import json
import os

ep_ids = [104379472, 104377247, 104375024, 104372794, 104270217, 104160898]

for eid in ep_ids:
    url = f"https://www.kaggle.com/api/v1/episodes/{eid}"
    print(f"Testing public download for episode {eid}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  --> Downloaded episode {eid}! Size: {len(str(data)):,} chars")
    except Exception as e:
        print(f"  --> Failed: {e}")
