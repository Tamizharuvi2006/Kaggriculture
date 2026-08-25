from __future__ import annotations

import json
import subprocess
from pathlib import Path

PYTHON = r"C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe"
ROOT = Path("reports/step5b/old_loss_gauntlet")
INVENTORY = ROOT / "submission_episode_inventory.json"
REPLAY_ROOT = ROOT / "raw_replays"
LIMIT_BY_LABEL = {"APEX35": 10}

inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
records = []

for label, data in inventory["submissions"].items():
    episodes = [e for e in data["episodes"] if "COMPLETED" in str(e.get("state", ""))]
    for episode in episodes[:LIMIT_BY_LABEL.get(label, 2)]:
        episode_id = episode["id"]
        folder = REPLAY_ROOT / episode_id
        replay_path = folder / f"episode-{episode_id}-replay.json"
        folder.mkdir(parents=True, exist_ok=True)
        if not replay_path.exists():
            subprocess.run(
                [PYTHON, "-m", "kaggle", "competitions", "replay", episode_id, "--path", str(folder)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        agents = replay.get("info", {}).get("Agents", [])
        rewards = replay.get("rewards", [])
        old_player = 0
        if agents and agents[0].get("Name") != "Tamizharuvi":
            old_player = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
        opponent = 1 - old_player
        records.append({
            "historical_label": label,
            "submission_id": data["submission_id"],
            "episode_id": episode_id,
            "seed": replay.get("info", {}).get("seed"),
            "agents": [a.get("Name") for a in agents],
            "old_player_index": old_player,
            "opponent_player_index": opponent,
            "old_reward": rewards[old_player] if len(rewards) > old_player else None,
            "opponent_reward": rewards[opponent] if len(rewards) > opponent else None,
            "old_model_lost": len(rewards) > opponent and rewards[old_player] < rewards[opponent],
            "transitions": max(0, len(replay.get("steps", [])) - 1),
            "replay_path": str(replay_path),
        })

out = ROOT / "historical_replay_summary.json"
out.write_text(json.dumps({"records": records}, indent=2), encoding="utf-8")
for record in records:
    print(
        f"{record['historical_label']:15} episode={record['episode_id']} "
        f"seed={record['seed']} old={record['old_reward']} "
        f"opp={record['opponent_reward']} loss={record['old_model_lost']}"
    )
print(f"WROTE {out}")
