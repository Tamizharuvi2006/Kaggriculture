import urllib.request, json, os

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH) as f:
        headers["Authorization"] = f"Bearer {f.read().strip()}"

req = urllib.request.Request(
    "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
    data=json.dumps({"submissionId": 55979565}).encode("utf-8"),
    headers=headers,
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        eps = data.get("episodes", [])
        print(f"Total episodes found: {len(eps)}")
        wins, losses = 0, 0
        rewards_list = []
        for ep in eps:
            agents = ep.get("agents", [])
            rewards = [a.get("reward", 0) for a in agents]
            sids = [a.get("submissionId") for a in agents]
            elos = [a.get("updatedScore") for a in agents]
            if len(sids) >= 2 and sids[0] != sids[1]:
                our_idx = 0 if sids[0] == 55979565 else 1
                our_r = rewards[our_idx]
                opp_r = rewards[1 - our_idx]
                our_elo = elos[our_idx]
                res = "WIN" if our_r > opp_r else "LOSS"
                if res == "WIN": wins += 1
                else: losses += 1
                rewards_list.append(our_r)
                print(f"Ep {ep.get('id')}: Our: ${our_r:>6,d} | Opp: ${opp_r:>6,d} | {res:<4} | Elo: {our_elo}")
        if wins + losses > 0:
            print("-" * 55)
            print(f"Competitive Record: {wins} W - {losses} L ({wins/(wins+losses)*100:.1f}%)")
            print(f"Avg Reward (All Competitive): ${sum(rewards_list)/len(rewards_list):,.0f}")
            print(f"Max Reward: ${max(rewards_list):,.0f}")
except Exception as e:
    print("Error:", e)
