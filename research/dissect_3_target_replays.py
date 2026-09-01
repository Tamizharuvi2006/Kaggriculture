"""Forensic Divergence Analyzer for Target Upper-Tier Matches:
104523414 (861 Elo Loss: $106k vs $117k)
104526077 (841 Elo Loss: $111k vs $120k)
104522963 (881 Elo Win:  $78k vs $62k)
"""
import json
import sys
import urllib.request
from pathlib import Path

TARGET_EPISODES = [
    {"id": 104523414, "label": "861 Elo Loss ($106k vs $117k)", "hero_seat": 0},
    {"id": 104526077, "label": "841 Elo Loss ($111k vs $120k)", "hero_seat": 1},
    {"id": 104522963, "label": "881 Elo Win  ($78k vs $62k)",  "hero_seat": 1},
]

OUTPUT_DIR = Path(r"D:\kaggriculture\reports\live_match_telemetry")

def download_replay(ep_id: int) -> Path:
    target_path = OUTPUT_DIR / f"episode-{ep_id}-replay.json"
    if target_path.exists() and target_path.stat().st_size > 10000:
        return target_path
    
    url = f"https://storage.googleapis.com/kaggle-episodes/{ep_id}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            target_path.write_bytes(data)
            print(f"[+] Downloaded {ep_id}: {len(data):,} bytes")
            return target_path
    except Exception as e:
        print(f"[-] Replay {ep_id} not available on GCS yet ({e})")
        return None

def analyze_replay(replay_path: Path, hero_seat: int, label: str):
    print("=" * 110)
    print(f"FORENSIC DIVERGENCE: {label} (Episode {replay_path.stem})")
    print("=" * 110)
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    steps = data.get("steps", [])
    if not steps:
        print("No steps found in replay!")
        return

    opp_seat = 1 - hero_seat
    persistent_step = None
    divergence_notes = []

    print(f"{'Step':<5} | {'Day:Hr':<6} | {'Hero Cash':<11} | {'Opp Cash':<11} | {'Deficit':<10} | {'Hero Herd':<10} | {'Opp Herd':<10} | {'Hero Q':<6} | {'Opp Q':<6}")
    print("-" * 110)

    for s_idx, step_obj in enumerate(steps):
        # Step obj is usually a list of [agent0_state, agent1_state]
        if not isinstance(step_obj, list) or len(step_obj) < 2:
            continue
        h_obs = step_obj[hero_seat].get("observation", {})
        o_obs = step_obj[opp_seat].get("observation", {})
        
        # State may be inside step_obj[0].observation.farms
        farms = h_obs.get("farms", []) or o_obs.get("farms", [])
        if len(farms) < 2:
            continue
            
        h_farm = farms[hero_seat]
        o_farm = farms[opp_seat]

        h_cash = float(h_farm.get("money", 0.0))
        o_cash = float(o_farm.get("money", 0.0))
        deficit = o_cash - h_cash

        # Count animals
        h_cows, h_sheep = 0, 0
        for r in (h_farm.get("tiles") or []):
            for t in r:
                if isinstance(t, dict):
                    if t.get("animal") == "COW": h_cows += 1
                    elif t.get("animal") == "SHEEP": h_sheep += 1
        h_herd = f"{h_cows}c/{h_sheep}s"

        o_cows, o_sheep = 0, 0
        for r in (o_farm.get("tiles") or []):
            for t in r:
                if isinstance(t, dict):
                    if t.get("animal") == "COW": o_cows += 1
                    elif t.get("animal") == "SHEEP": o_sheep += 1
        o_herd = f"{o_cows}c/{o_sheep}s"

        h_quads = len(h_farm.get("unlocked_quadrants", []) or [])
        o_quads = len(o_farm.get("unlocked_quadrants", []) or [])

        day = s_idx // 24
        hr = s_idx % 24

        # Track persistent deficit
        if deficit > 3000.0 and persistent_step is None and s_idx > 48:
            persistent_step = s_idx

        # Print snapshot every day (every 24 steps) or when persistent deficit hits
        if s_idx % 48 == 0 or s_idx == persistent_step or s_idx == len(steps) - 1:
            marker = " <-- DIVERGENCE" if s_idx == persistent_step else ""
            print(f"{s_idx:<5} | D{day:02d}:H{hr:02d} | ${h_cash:10,.0f} | ${o_cash:10,.0f} | ${deficit:+9,.0f} | {h_herd:<10} | {o_herd:<10} | {h_quads:<6} | {o_quads:<6}{marker}")

    print("-" * 110)
    if persistent_step is not None:
        p_day = persistent_step // 24
        p_hr = persistent_step % 24
        print(f"--> First persistent deficit occurred at Step {persistent_step} (Day {p_day}, Hour {p_hr})")
    else:
        print("--> No persistent deficit > $3,000 observed during standard play.")
    print("\n")

def main():
    ready_count = 0
    for ep in TARGET_EPISODES:
        path = download_replay(ep["id"])
        if path and path.exists():
            analyze_replay(path, ep["hero_seat"], ep["label"])
            ready_count += 1
            
    if ready_count == 0:
        print("[!] None of the target replays are available on GCS yet.")
        print("[*] Kaggle GCS sync is still pending. Re-run this script once batch sync triggers.")

if __name__ == "__main__":
    main()
