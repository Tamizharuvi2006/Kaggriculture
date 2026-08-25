"""Test competition slug for upload."""
import os
import json
import urllib.request

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
with open(TOKEN_PATH, "r", encoding="utf-8") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

competitions = ["kaggriculture", "lux-ai-season-3", "kaggriculture-season-1", "kaggriculture-2025", "kaggriculture-s1"]

for comp in competitions:
    url = f"https://www.kaggle.com/api/v1/competitions/submissions/list/{comp}"
    print(f"Testing list for '{comp}'...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  -> SUCCESS! Found {len(data)} submissions for '{comp}'.")
    except Exception as e:
        print(f"  -> Failed for '{comp}': {e}")
