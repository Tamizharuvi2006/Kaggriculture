"""Test querying ListEpisodes on opponent submission IDs to crawl up the ladder."""
import os
import json
import urllib.request
import urllib.error

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# Test opponent submission IDs from our recent matches
test_opp_subs = [
    55787488, # 1157.2 Elo
    55787770, # 962.9 Elo
    55788975, # 911.7 Elo
    55309911, # 1078.8 Elo
    55242320, # 1001.4 Elo
]

def query_sub_episodes(sub_id: int):
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
    payload = json.dumps({"submissionId": int(sub_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            eps = data.get("episodes", [])
            print(f"  -> SUCCESS for Sub {sub_id}! Retrieved {len(eps)} matches.")
            # Find opponents in their matches
            opp_ratings = []
            for ep in eps:
                for a in ep.get("agents", []):
                    if a.get("submissionId") != sub_id:
                        opp_ratings.append(float(a.get("initialScore") or 0.0))
            if opp_ratings:
                print(f"     Opponent ratings range: {min(opp_ratings):.1f} - {max(opp_ratings):.1f} (Mean: {sum(opp_ratings)/len(opp_ratings):.1f})")
            return eps
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code} for Sub {sub_id}: {e.reason}")
    except Exception as e:
        print(f"  -> Error: {e}")
    return []

for s in test_opp_subs:
    print(f"\nQuerying episodes for Opponent Submission {s}...")
    query_sub_episodes(s)
