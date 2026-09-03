import gzip, json

def inspect_match(ep_id, seat, label):
    path = f"D:/kaggriculture/data/hf_il/cache/{ep_id}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        rep = json.load(f)
    steps = rep["steps"]
    
    print(f"\n=== {label} (Ep {ep_id}, Seat {seat}) ===")
    for day in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28):
        s = day * 24 + 1
        if s >= len(steps): break
        obs = steps[s][seat]["observation"]
        farm = obs["farms"][seat]
        priv = obs.get("private", {}) or {}
        shed = priv.get("shed", {}) or {}
        
        # Count sales in previous 24 hours
        sales = {}
        for prev_s in range(max(0, s - 24), s):
            act = steps[prev_s][seat].get("action", {}) or {}
            for m in act.get("market", []) or []:
                if m and len(m) >= 3 and m[0] == "SELL":
                    sales[m[1]] = sales.get(m[1], 0) + int(m[2])
                    
        sales_str = " ".join(f"{k}:{v}" for k, v in sorted(sales.items())) if sales else "None"
        cash = int(farm.get("money", 0))
        print("D%02d | Cash: $%7d | Hands: %2d | Prev24h Sales: %s" % (day, cash, len(farm.get("hands", [])), sales_str))

inspect_match(90610832, 0, "TIER 1: JeovaAnderson ($55,386)")
inspect_match(95509135, 0, "TIER 4: ReCurSiON ($141,498)")
inspect_match(90561400, 0, "TIER 4: Kaito Fukami ($150,620)")
