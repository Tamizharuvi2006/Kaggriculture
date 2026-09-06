import urllib.request, json, os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
headers = {"User-Agent": "Mozilla/5.0"}
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH) as f:
        headers["Authorization"] = f"Bearer {f.read().strip()}"

req = urllib.request.Request(
    "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
    data=json.dumps({"submissionId": 55979565}).encode("utf-8"),
    headers={"Content-Type": "application/json", **headers},
    method="POST"
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    eps = data.get("episodes", [])

print(f"Total episodes: {len(eps)}")
results = []
for ep in eps:
    ep_id = ep["id"]
    agents = ep.get("agents", [])
    rewards = [a.get("reward", 0) for a in agents]
    sids = [a.get("submissionId") for a in agents]
    if len(sids) >= 2 and sids[0] != sids[1]:
        our_idx = 0 if sids[0] == 55979565 else 1
        our_r = rewards[our_idx]
        opp_r = rewards[1 - our_idx]
        seed = ep.get("seed", 0)
        results.append({
            "id": ep_id,
            "our_reward": our_r,
            "opp_reward": opp_r,
            "win": our_r > opp_r,
            "margin": our_r - opp_r,
            "seed": seed
        })

print(f"{'Episode':<11} | {'Our':>8} | {'Opp':>8} | {'Margin':>9} | {'Win':<5} | {'Seed':>12}")
print("-" * 65)
for r in results:
    print(f"{r['id']:<11} | ${r['our_reward']:>7,d} | ${r['opp_reward']:>7,d} | ${r['margin']:>+8,d} | {str(r['win']):<5} | {r['seed']:>12}")

wins = [r for r in results if r["win"]]
losses = [r for r in results if not r["win"]]
print("-" * 65)
print(f"Wins: {len(wins)} | Losses: {len(losses)} | Win Rate: {len(wins)/len(results)*100:.1f}%")
print(f"Average Win Score: ${sum(r['our_reward'] for r in wins)/len(wins):,.0f}")
print(f"Average Loss Score: ${sum(r['our_reward'] for r in losses)/len(losses):,.0f}")
print(f"Average Opponent Score in Losses: ${sum(r['opp_reward'] for r in losses)/len(losses):,.0f}")
