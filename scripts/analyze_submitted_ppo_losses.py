from __future__ import annotations

import json
import subprocess
from pathlib import Path

PYTHON = r"C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe"
ROOT = Path("reports/step5b/old_loss_gauntlet/ppo_submission_replays")
ROOT.mkdir(parents=True, exist_ok=True)
EPISODES = [
    "96197962", "96195656", "96193374", "96191104", "96188812",
    "96186500", "96184199", "96181915", "96179642", "96177375", "96175431",
]

records = []
for episode_id in EPISODES:
    folder = ROOT / episode_id
    path = folder / f"episode-{episode_id}-replay.json"
    folder.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        subprocess.run(
            [PYTHON, "-m", "kaggle", "competitions", "replay", episode_id, "--path", str(folder)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    replay = json.loads(path.read_text(encoding="utf-8"))
    agents = replay.get("info", {}).get("Agents", [])
    rewards = replay.get("rewards", [])
    ppo_index = next((i for i, a in enumerate(agents) if a.get("Name") == "Tamizharuvi"), 0)
    opp_index = 1 - ppo_index
    steps = replay.get("steps", [])
    ppo_reward = float(rewards[ppo_index]) if len(rewards) > ppo_index else None
    opp_reward = float(rewards[opp_index]) if len(rewards) > opp_index else None
    final = steps[-1] if steps else []
    ppo_obs = final[ppo_index].get("observation", {}) if len(final) > ppo_index else {}
    opp_obs = final[opp_index].get("observation", {}) if len(final) > opp_index else {}
    ppo_farm = (ppo_obs.get("farms") or [{}])[0]
    opp_farm = (opp_obs.get("farms") or [{}])[0]
    late_actions = []
    for step_index in range(max(0, len(steps) - 120), len(steps)):
        frame = steps[step_index]
        if len(frame) > ppo_index:
            late_actions.append({
                "step": step_index,
                "day": frame[ppo_index].get("observation", {}).get("day"),
                "action": frame[ppo_index].get("action"),
            })
    records.append({
        "episode_id": episode_id,
        "type": "validation" if episode_id == "96175431" else "public",
        "seed": replay.get("info", {}).get("seed"),
        "agents": [a.get("Name") for a in agents],
        "ppo_index": ppo_index,
        "ppo_reward": ppo_reward,
        "opponent_reward": opp_reward,
        "margin": None if ppo_reward is None or opp_reward is None else ppo_reward - opp_reward,
        "loss": ppo_reward is not None and opp_reward is not None and ppo_reward < opp_reward,
        "steps": len(steps),
        "ppo_final_money": ppo_farm.get("money"),
        "opponent_final_money": opp_farm.get("money"),
        "ppo_final_farmer": ppo_farm.get("farmer"),
        "opponent_final_farmer": opp_farm.get("farmer"),
        "ppo_final_tiles": ppo_farm.get("tiles"),
        "opponent_final_tiles": opp_farm.get("tiles"),
        "late_actions": late_actions,
        "replay_path": str(path),
    })

out = Path("reports/step5b/old_loss_gauntlet/submitted_ppo_loss_analysis.json")
out.write_text(json.dumps({"submission": "55674870", "records": records}, indent=2), encoding="utf-8")
print(f"episodes={len(records)} losses={sum(r['loss'] for r in records)} wins={sum(not r['loss'] for r in records)}")
for r in records:
    print(f"{r['episode_id']} {r['type']:10} PPO={r['ppo_reward']} OPP={r['opponent_reward']} margin={r['margin']} loss={r['loss']}")
print(f"WROTE {out}")
