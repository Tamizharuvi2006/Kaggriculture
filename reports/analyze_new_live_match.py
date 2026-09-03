import json, os, sys, urllib.request

def analyze_live_match(file_or_id):
    ep_data = None
    if os.path.exists(file_or_id):
        with open(file_or_id, "r", encoding="utf-8") as f:
            ep_data = json.load(f)
    else:
        # Try fetching via Kaggle API URL or public replay store
        ep_id = str(file_or_id).strip()
        bucket = ep_id[-2:]
        url = f"https://huggingface.co/datasets/KiroSamurai/kaggriculture-il/resolve/main/datasets/il/episodes/{bucket}/{ep_id}.json.gz"
        try:
            import gzip
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                decomp = gzip.decompress(resp.read())
                ep_data = json.loads(decomp.decode("utf-8"))
        except Exception:
            # Try direct Kaggle episode url
            kaggle_url = f"https://www.kaggle.com/api/v1/episodes/{ep_id}"
            req = urllib.request.Request(kaggle_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                ep_data = json.loads(resp.read().decode("utf-8"))

    if not ep_data:
        print(f"Could not load episode data for {file_or_id}")
        return

    steps = ep_data.get("steps", [])
    rewards = ep_data.get("rewards") or [steps[-1][0].get("reward", 0), steps[-1][1].get("reward", 0)]
    
    print("=" * 95)
    print(f"     LIVE MATCH FORENSIC AUDIT (Total Steps: {len(steps)})     ")
    print(f"     Final Rewards: Agent 0 = ${rewards[0]:,.0f} vs Agent 1 = ${rewards[1]:,.0f}")
    print("=" * 95)
    
    for day in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28):
        s = day * 24 + 1
        if s >= len(steps): break
        
        row_str = f"Day {day:02d} | "
        for seat in (0, 1):
            obs = steps[s][seat].get("observation", {})
            farms = obs.get("farms", [])
            if len(farms) <= seat: continue
            farm = farms[seat]
            cash = int(farm.get("money", 0))
            hands = len(farm.get("hands", []))
            lands = len(farm.get("unlocked_quadrants", ["NW"]))
            
            anims = 0
            for row in farm.get("tiles", []):
                for t in row:
                    if isinstance(t, dict) and t.get("animal"):
                        anims += 1
            row_str += f"[P{seat}: Cash ${cash:>6,d} | H:{hands:>2} L:{lands} A:{anims:>2}]  "
        print(row_str)
        
    print("=" * 95)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_live_match(sys.argv[1])
    else:
        print("Usage: python reports/analyze_new_live_match.py <replay_file_or_episode_id>")
