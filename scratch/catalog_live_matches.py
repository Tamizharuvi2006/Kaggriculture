import urllib.request
import json
import os

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

def list_eps(sid):
    req = urllib.request.Request(
        "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
        data=json.dumps({"submissionId": int(sid)}).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

all_matches = {}

for sid in [55924297, 55924286]:
    data = list_eps(sid)
    eps = data.get("episodes", [])
    wins, losses, ties = 0, 0, 0
    records = []
    print(f"=== SUBMISSION {sid} (Total episodes: {len(eps)}) ===")
    for ep in eps:
        ep_id = ep.get("id")
        agents = ep.get("agents", [])
        our_idx = None
        for i, a in enumerate(agents):
            if a.get("submissionId") == sid:
                our_idx = i
                break
        if our_idx is None:
            continue
        opp_idx = 1 - our_idx
        our_score = agents[our_idx].get("reward")
        opp_score = agents[opp_idx].get("reward") if len(agents) > 1 else None
        opp_sid = agents[opp_idx].get("submissionId") if len(agents) > 1 else None
        opp_elo = agents[opp_idx].get("initialScore") if len(agents) > 1 else None
        our_elo = agents[our_idx].get("initialScore")
        seed = ep.get("seed")
        
        res = "UNKNOWN"
        if our_score is not None and opp_score is not None:
            if our_score > opp_score:
                res = "WIN"
                wins += 1
            elif our_score < opp_score:
                res = "LOSS"
                losses += 1
            else:
                res = "TIE"
                ties += 1
        
        record = {
            "episode_id": ep_id,
            "result": res,
            "submission_id": sid,
            "our_seat": our_idx,
            "our_score": our_score,
            "opp_score": opp_score,
            "opp_sid": opp_sid,
            "opp_elo": opp_elo,
            "our_elo": our_elo,
            "seed": seed,
            "createTime": ep.get("createTime"),
            "state": ep.get("state")
        }
        records.append(record)
        opp_elo_str = f"{float(opp_elo):.1f}" if opp_elo is not None else "N/A"
        print(f"Ep {ep_id:9d} | {res:4s} | Seat {our_idx} | Ours: {str(our_score):>7s} vs Opp({opp_sid}, Elo {opp_elo_str:>6s}): {str(opp_score):>7s} | Seed: {seed}")
        
    total = wins + losses + ties
    wr = (wins / total * 100) if total > 0 else 0
    print(f"\nSummary for {sid}: Wins={wins}, Losses={losses}, Ties={ties}, Total={total}, Win Rate={wr:.1f}%\n")
    all_matches[str(sid)] = records

with open(os.path.join(OUTPUT_DIR, "live_matches_exp208_catalog.json"), "w", encoding="utf-8") as f:
    json.dump(all_matches, f, indent=2)

print(f"Saved match catalog to reports/live_match_telemetry/live_matches_exp208_catalog.json")
