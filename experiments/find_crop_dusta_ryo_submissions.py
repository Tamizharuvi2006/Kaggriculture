"""Search telemetry JSONs specifically for Top 5 Team IDs."""
import os
import json
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_TEAMS = {
    16714457: "Crop Dusta (#1, 3090.2)",
    16644287: "Ryo Hasegawa (#2, 3030.3)",
    16705390: "Subramanya N (#3, 2967.6)",
    16730065: "Blu3s (#4, 2897.2)",
    16665224: "tyz123456 (#5, 2893.8)",
}

target_dirs = [
    os.path.join(BASE_DIR, "reports", "live_match_telemetry"),
    os.path.join(BASE_DIR, "reports", "live_match_telemetry", "grandmaster_replays"),
    os.path.join(BASE_DIR, "reports", "live_match_telemetry", "d1_live_matches"),
]

found = []
for d in target_dirs:
    for f in glob.glob(os.path.join(d, "*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            eps = []
            if isinstance(data, dict):
                if "episodes" in data and isinstance(data["episodes"], list):
                    eps = data["episodes"]
                elif "episode" in data and isinstance(data["episode"], dict):
                    eps = [data["episode"]]
                elif "matches" in data and isinstance(data["matches"], list):
                    eps = data["matches"]

            for ep in eps:
                for a in ep.get("agents", []):
                    t_id = a.get("teamId")
                    if t_id in TARGET_TEAMS:
                        found.append({
                            "team": TARGET_TEAMS[t_id],
                            "teamId": t_id,
                            "submissionId": a.get("submissionId"),
                            "score": a.get("initialScore"),
                            "ep_id": ep.get("id"),
                            "seed": ep.get("seed"),
                        })
        except Exception:
            continue

print(f"Discovered {len(found)} direct matches for Top 5 Leaderboard Teams:")
for m in found:
    print(f"  -> {m['team']}: Sub ID {m['submissionId']} | Episode {m['ep_id']} (Seed: {m['seed']}) | Score: {m['score']}")
