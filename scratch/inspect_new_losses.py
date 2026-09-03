import json

for eid in [104514771, 104515647]:
    path = f"reports/live_match_telemetry/episode-{eid}-replay.json"
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    info = d.get("info", {})
    agents = info.get("Agents", [])
    rewards = d.get("rewards", [])
    seed = info.get("seed")
    print(f"\nEpisode {eid} (Seed {seed}):")
    for i, a in enumerate(agents):
        print(f"  P{i}: {a.get('Name')} | Initial Score: {a.get('initialScore')} | Reward: ${rewards[i]:,.0f}")
