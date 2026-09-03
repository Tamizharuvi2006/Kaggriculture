import os, json

cache_dir = r"D:\kaggriculture\reports\live_match_telemetry\all_loss_replays_cache"
our_matches = []
for f in os.listdir(cache_dir):
    if f.endswith(".json"):
        path = os.path.join(cache_dir, f)
        try:
            with open(path) as fp:
                data = json.load(fp)
            agents = data.get("episode", {}).get("agents", [])
            if len(agents) >= 2:
                our_matches.append({
                    "file": f,
                    "ep_id": data.get("episode", {}).get("id"),
                    "p0_score": agents[0].get("initialScore", 0),
                    "p1_score": agents[1].get("initialScore", 0),
                    "p0_reward": agents[0].get("reward", 0),
                    "p1_reward": agents[1].get("reward", 0),
                })
        except Exception:
            continue

print(f"Total live loss match records in all_loss_replays_cache: {len(our_matches)}")
if our_matches:
    p0_scores = [m["p0_score"] for m in our_matches]
    p1_scores = [m["p1_score"] for m in our_matches]
    print(f"Player 0 (Our bot) Elo range: {min(p0_scores):.1f} to {max(p0_scores):.1f} (Avg: {sum(p0_scores)/len(p0_scores):.1f})")
    print(f"Player 1 (Opponents) Elo range: {min(p1_scores):.1f} to {max(p1_scores):.1f} (Avg: {sum(p1_scores)/len(p1_scores):.1f})")
    print("\nSample 10 live loss matches:")
    for m in our_matches[:10]:
        print(f"  Ep {m['ep_id']} ({m['file']}): Our Elo={m['p0_score']:.0f} (${m['p0_reward']:,}) vs Opp Elo={m['p1_score']:.0f} (${m['p1_reward']:,})")
