import subprocess
import os

episodes = [
    "104475527", # vs 982 Elo (-$43k)
    "104424149", # vs 884 Elo (-$39k)
    "104433117", # vs 882 Elo (-$29k)
    "104388418", # vs 1011 Elo (-$27k)
]

out_dir = r"D:\kaggriculture\reports\live_match_telemetry"
python_exe = r"C:\Users\aruvi\AppData\Local\Programs\Python\Python313\python.exe"

for ep in episodes:
    target_path = os.path.join(out_dir, f"episode-{ep}-replay.json")
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000000:
        print(f"Already downloaded {ep}")
        continue
    print(f"Downloading replay for {ep}...")
    res = subprocess.run([python_exe, "-m", "kaggle", "competitions", "replay", ep, "--path", out_dir], capture_output=True, text=True)
    print(f"Done {ep}: {res.stdout.strip()}")
