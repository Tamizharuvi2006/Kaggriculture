import json

with open("D:/kaggriculture/reports/step5b/old_loss_gauntlet/raw_replays/91697084/episode-91697084-replay.json") as f:
    rep = json.load(f)

steps = rep["steps"]

print("=" * 100)
print("MAOU ($146,972) STEP 0..120 FORENSIC ACTION & REVENUE DISSECTION")
print("=" * 100)

for s in range(121):
    st = steps[s]
    obs = st[0]["observation"]
    action = st[0].get("action")
    farm = obs["farms"][0]
    priv = obs["private"]
    money = farm["money"]
    day = obs["day"]
    hour = obs["hour"]
    
    # Check if there were market orders or interesting unit actions
    market = action.get("market", []) if isinstance(action, dict) else []
    farmer = action.get("farmer", []) if isinstance(action, dict) else []
    hands = action.get("hands", []) if isinstance(action, dict) else []
    
    # Check non-pass actions
    has_action = bool(market) or any(h != ["PASS"] for h in hands) or (farmer and farmer != ["PASS"])
    
    if has_action or s % 24 == 0 or s in [4, 6, 12, 24, 48, 72, 96, 120]:
        print(f"Step {s:3d} (D{day:2d}:H{hour:2d}) | Money: ${money:7.1f} | Farmer: {farmer} | Hands({len(hands)}): {hands[:2]} | Market: {market}")
