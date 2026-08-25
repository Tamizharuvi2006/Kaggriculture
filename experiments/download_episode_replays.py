"""Download full step-by-step replay JSONs for 1100-1300 tier matches of APEX 3.5.
"""

from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "apex35_replays")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"

def get_headers():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def fetch_episode_replay(ep_id: int):
    headers = get_headers()
    url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ShowEpisode"
    payload = json.dumps({"episodeId": int(ep_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching episode {ep_id}: {e}")
        return None

def main():
    data_path = os.path.join(BASE_DIR, "reports", "live_match_telemetry", "submission_55483322_episodes.json")
    with open(data_path, "r", encoding="utf-8") as f:
        sub_data = json.load(f)

    episodes = sub_data.get("episodes", [])
    sub_id = 55483322

    target_episodes = []
    for ep in episodes:
        agents = ep.get("agents", [])
        if len(agents) < 2: continue
        our_ag = next((a for a in agents if a.get("submissionId") == sub_id), None)
        opp_ag = next((a for a in agents if a.get("submissionId") != sub_id), None)
        if not our_ag or not opp_ag: continue

        opp_score = float(opp_ag.get("initialScore") or 0.0)
        our_rew = float(our_ag.get("reward") or 0.0)
        opp_rew = float(opp_ag.get("reward") or 0.0)

        # 1100-1300 tier matches
        if 1100 <= opp_score < 1300:
            target_episodes.append({
                "ep_id": ep.get("id"),
                "opp_score": opp_score,
                "opp_sub": opp_ag.get("submissionId"),
                "our_reward": our_rew,
                "opp_reward": opp_rew,
                "is_loss": 1 if our_rew < opp_rew else 0
            })

    print(f"Found {len(target_episodes)} total matches in 1100-1300 tier ({sum(e['is_loss'] for e in target_episodes)} Losses, {len(target_episodes) - sum(e['is_loss'] for e in target_episodes)} Wins).")

    for i, t in enumerate(target_episodes):
        ep_id = t["ep_id"]
        out_file = os.path.join(OUTPUT_DIR, f"episode_{ep_id}.json")
        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
            print(f"[{i+1}/{len(target_episodes)}] Episode {ep_id} already cached.")
            continue

        print(f"[{i+1}/{len(target_episodes)}] Fetching Episode {ep_id} (Opp Elo: {t['opp_score']:.1f}, Loss: {t['is_loss']})...", flush=True)
        rep = fetch_episode_replay(ep_id)
        if rep:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(rep, f)

    print("\n✅ All target episode replays downloaded successfully!")

if __name__ == "__main__":
    main()
