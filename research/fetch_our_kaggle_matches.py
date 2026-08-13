from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_PATH = r"C:\Users\43731140\.kaggle\access_token"

def main():
    if not os.path.exists(TOKEN_PATH):
        print(f"Token not found at {TOKEN_PATH}")
        return

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    print(f"Using Bearer Token (length {len(token)} chars)...")

    # Possible competition slugs
    competitions = ["kaggriculture", "lux-ai-season-3", "kaggriculture-season-1", "kaggriculture-2025"]

    for comp in competitions:
        url = f"https://www.kaggle.com/api/v1/competitions/submissions/list/{comp}"
        print(f"\nQuerying submissions for '{comp}' -> {url}")
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"  ✅ Success! Found {len(data)} submissions:")
                for s in data:
                    print(f"    - ID: {s.get('id')}, Date: {s.get('date')}, Status: {s.get('status')}, Score: {s.get('publicScore')}, Desc: {s.get('description', '')[:70]}")
        except urllib.error.HTTPError as e:
            print(f"  ❌ HTTP {e.code}: {e.reason}")
            try:
                print("     Body:", e.read().decode("utf-8")[:200])
            except Exception:
                pass
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    main()
