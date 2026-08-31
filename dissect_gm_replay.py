import json

replay_path = "D:/kaggriculture/reports/step5b/old_loss_gauntlet/raw_replays/91697084/episode-91697084-replay.json"

with open(replay_path, "r") as f:
    replay = json.load(f)

steps = replay["steps"]
print(f"Total steps in replay: {len(steps)}")

# Dissect Seat 0 (Winner: $146,972) and Seat 1 ($137,306) across Step 0..360
checkpoints = [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360]

print("=" * 90)
print(f"{'Step':>4} | {'Day':>3} | {'P0 Cash':>8} | {'P0 Land':>7} | {'P0 Hands':>8} | {'P0 Animals':>10} | {'P0 Crops':>20} | {'P0 Orders'}")
print("=" * 90)

for s in range(min(361, len(steps))):
    st = steps[s]
    # State inspection
    # In kaggle replay: observation is in st[0]["observation"] or st[player]["observation"]
    obs0 = st[0].get("observation", {})
    info0 = st[0].get("info", {})
    action0 = st[0].get("action", {})
    
    # Check if this step is a checkpoint or has key market/land/unit actions
    if s in checkpoints or (action0 and any(action0.values())):
        day = s // 24
        # Let's inspect action0
        market_orders = action0.get("market", []) if isinstance(action0, dict) else []
        worker_actions = action0.get("hands", []) if isinstance(action0, dict) else []
        farmer_action = action0.get("farmer", []) if isinstance(action0, dict) else []
        
        # Check reward/cash if available
        r0 = st[0].get("reward", None)
        
        # Let's see what is inside obs0
        # If obs0 has raw state or board
        pass

# Let's inspect step 0 and step 1 format in detail
print("Step 0 st[0] keys:", steps[0][0].keys())
print("Step 1 st[0] action:", steps[1][0].get("action"))
if "observation" in steps[1][0]:
    print("Step 1 st[0] obs keys:", steps[1][0]["observation"].keys())
