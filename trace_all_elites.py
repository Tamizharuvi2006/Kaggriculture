import json
import os

replay_paths = [
    "D:/kaggriculture/reports/step5b/old_loss_gauntlet/raw_replays/91697084/episode-91697084-replay.json",
    "D:/kaggriculture/reports/step5b/old_loss_gauntlet/ppo_submission_replays/96177375/episode-96177375-replay.json",
    "D:/kaggriculture/reports/step5b/old_loss_gauntlet/ppo_submission_replays/96197962/episode-96197962-replay.json",
    "D:/kaggriculture/reports/step5b/old_loss_gauntlet/ppo_submission_replays/96191104/episode-96191104-replay.json",
    "D:/kaggriculture/reports/step5b/old_loss_gauntlet/ppo_submission_replays/96181915/episode-96181915-replay.json"
]

def analyze_replay(r_path):
    with open(r_path, "r") as f:
        data = json.load(f)
    steps = data["steps"]
    
    # Determine winner
    last = steps[-1]
    p0_rew = last[0].get("reward", 0.0) or 0.0
    p1_rew = last[1].get("reward", 0.0) or 0.0
    winner = 0 if p0_rew > p1_rew else 1
    win_rew = max(p0_rew, p1_rew)
    
    print("=" * 100)
    print(f"REPLAY: {os.path.basename(r_path)} | Winner: Player {winner} (${win_rew:,.0f}) vs P{1-winner} (${min(p0_rew, p1_rew):,.0f})")
    print("=" * 100)
    
    checkpoints = [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360]
    
    # Track inventory, cash, animals, crops at checkpoints
    for s in checkpoints:
        if s >= len(steps):
            break
        st = steps[s]
        obs = st[winner].get("observation", {})
        day = obs.get("day", s // 24)
        hour = obs.get("hour", s % 24)
        
        farms = obs.get("farms", [{}, {}])
        w_farm = farms[winner] if len(farms) > winner else {}
        w_priv = obs.get("private", {})
        
        cash = w_farm.get("money", 0.0)
        hands = len(w_farm.get("hands", []))
        quads = len(w_farm.get("unlocked_quadrants", []))
        
        # Count tiles
        tiles = w_farm.get("tiles", [])
        cows = 0
        sheep = 0
        crops = {}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    k = t.get("kind")
                    if k == "ANIMAL":
                        a_name = t.get("animal")
                        if a_name == "COW": cows += 1
                        elif a_name == "SHEEP": sheep += 1
                    elif k == "PLANT":
                        c_name = t.get("crop")
                        crops[c_name] = crops.get(c_name, 0) + 1
        
        crop_summary = ", ".join([f"{k}:{v}" for k, v in sorted(crops.items())])
        
        # Action at this step
        act = st[winner].get("action", {})
        market_act = act.get("market", []) if isinstance(act, dict) else []
        m_summary = ""
        if market_act:
            m_summary = str(market_act)
            if len(m_summary) > 40:
                m_summary = m_summary[:37] + "..."
                
        print(f"Step {s:3d} (D{day:2d}:H{hour:2d}) | Cash: ${cash:7.0f} | Q: {quads} | Hands: {hands:2d} | Cows: {cows:2d} | Sheep: {sheep:2d} | Crops: {crop_summary:<25} | Market: {m_summary}")

for rp in replay_paths:
    analyze_replay(rp)
