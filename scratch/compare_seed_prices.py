import gzip, json

def inspect_prices(ep_id, seat, label):
    path = f"D:/kaggriculture/data/hf_il/cache/{ep_id}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        rep = json.load(f)
    steps = rep["steps"]
    
    print(f"\n=== {label} (Ep {ep_id}) ===")
    for day in (1, 6, 12, 18, 24):
        s = day * 24 + 1
        if s >= len(steps): break
        obs = steps[s][seat]["observation"]
        prices = (obs.get("market", {}) or {}).get("prices", {}) or {}
        p_str = " ".join(f"{k}:{v:.0f}" for k, v in sorted(prices.items()) if k in ("MELON", "STRAWBERRY", "MILK", "WOOL", "WHEAT"))
        print(f"  D{day:02d} | Prices: {p_str}")

inspect_prices(90610832, 0, "Band 1 ($55k): JeovaAnderson")
inspect_prices(90561400, 0, "Band 5 ($150k): Kaito Fukami")
inspect_prices(94348150, 0, "Band 5 ($151k): HKmgikao")
