from __future__ import annotations

import json
import subprocess
from pathlib import Path

PYTHON = r"C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe"
SUBMISSIONS = {
    "L_PLUS": "55373932",
    "L_PLUS_PLUS": "55376463",
    "HYBRID_L_PLUS": "55373438",
    "APEX30": "55411304",
    "APEX33": "55421857",
    "APEX35": "55483322",
}

out = Path("reports/step5b/old_loss_gauntlet")
out.mkdir(parents=True, exist_ok=True)
inventory = {}

for label, submission_id in SUBMISSIONS.items():
    proc = subprocess.run(
        [PYTHON, "-m", "kaggle", "competitions", "episodes", submission_id, "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    decoder = json.JSONDecoder()
    start = proc.stdout.find("[")
    episodes, _ = decoder.raw_decode(proc.stdout[start:])
    inventory[label] = {
        "submission_id": submission_id,
        "episodes": [
            {
                "id": str(item["id"]),
                "create_time": item.get("createTime"),
                "end_time": item.get("endTime"),
                "state": item.get("state"),
                "type": item.get("type"),
            }
            for item in episodes
        ],
    }

report = {
    "purpose": "Historical old-loss gauntlet inventory; no training or submission",
    "submissions": inventory,
}
path = out / "submission_episode_inventory.json"
path.write_text(json.dumps(report, indent=2), encoding="utf-8")

for label, data in inventory.items():
    episodes = data["episodes"]
    print(f"{label:15} submission={data['submission_id']} episodes={len(episodes)}")
    for episode in episodes[:3]:
        print(f"  {episode['id']} {episode['type']} {episode['state']}")
print(f"WROTE {path}")
