"""Download latest Kaggle Submissions & Episodes and execute Win/Loss Forensic Analysis.
"""

import sys
import os
import json
import glob
import urllib.request
import urllib.parse

# Set encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPETITION_NAME = "lux-ai-season-3"

def get_kaggle_token():
    possible_paths = [
        os.path.expanduser(r"~\.kaggle\access_token"),
        r"C:\Users\aruvi\.kaggle\access_token",
        os.path.expanduser(r"~\.kaggle\kaggle.json"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    try:
                        data = json.loads(content)
                        return ("json", data)
                    except Exception:
                        pass
                else:
                    return ("bearer", content)
    return (None, None)

def fetch_submissions():
    print("Fetching latest Kaggle Submissions...", flush=True)
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        subs = api.competition_submissions(COMPETITION_NAME)
        print(f"Retrieved {len(subs)} submissions via KaggleApi CLI.", flush=True)
        return subs
    except Exception as e:
        print(f"KaggleApi client attempt: {e}", flush=True)

    token_type, token_val = get_kaggle_token()
    if token_type == "bearer":
        headers = {"Authorization": f"Bearer {token_val}"}
        url = f"https://www.kaggle.com/api/v1/competitions/submissions/list/{COMPETITION_NAME}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"Retrieved {len(data)} submissions via Kaggle Bearer API.", flush=True)
                return data
        except Exception as err:
            print(f"Bearer API attempt error: {err}", flush=True)
    elif token_type == "json":
        headers = {
            "Authorization": f"Bearer {token_val.get('key')}"
        }
        url = f"https://www.kaggle.com/api/v1/competitions/submissions/list/{COMPETITION_NAME}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"Retrieved submissions: {len(data)}", flush=True)
                return data
        except Exception as err:
            print(f"Json API attempt error: {err}", flush=True)
            
    print("Could not retrieve submissions directly via API.", flush=True)
    return []

def main():
    print("====================================================")
    print("KAGGRICULTURE LATEST SUBMISSION & REPLAY ENGINE")
    print("====================================================")
    
    subs = fetch_submissions()
    if subs:
        print("\n--- RECENT KAGGLE SUBMISSIONS ---")
        for sub in subs[:10]:
            if isinstance(sub, dict):
                sub_id = sub.get("id")
                date = sub.get("date")
                status = sub.get("status")
                desc = sub.get("description")
                score = sub.get("publicScore")
            else:
                sub_id = getattr(sub, "id", "N/A")
                date = getattr(sub, "date", "N/A")
                status = getattr(sub, "status", "N/A")
                desc = getattr(sub, "description", "N/A")
                score = getattr(sub, "publicScore", "N/A")
            print(f"ID: {sub_id} | Status: {status} | Score: {score} | Date: {date} | Desc: {desc}")
    else:
        print("No live Kaggle submissions returned via API or credentials.")

    # Sweep local replay directories
    search_dirs = [
        os.path.join(BASE_DIR, "l+reviews"),
        os.path.join(BASE_DIR, "l+reviews", "newl"),
        os.path.join(BASE_DIR, "l+reviews", "newl", "loss"),
        os.path.join(BASE_DIR, "l++reviews"),
        os.path.join(BASE_DIR, "l++reviews", "loss"),
    ]
    
    all_replays = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fpath in glob.glob(os.path.join(sdir, "*.json")):
                fname = os.path.basename(fpath)
                if fname.endswith("-0.json") or fname.endswith("-1.json"):
                    continue
                all_replays.append(fpath)
                
    all_replays = sorted(list(set(all_replays)))
    print(f"\nDissecting all {len(all_replays)} local replay files across review folders...")
    
    wins = 0
    losses = 0
    
    for rpath in all_replays:
        rel = os.path.relpath(rpath, BASE_DIR)
        try:
            with open(rpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            steps = data.get("steps", [])
            if not steps:
                continue
            last = steps[-1]
            p0 = last[0]["observation"]["farms"][0]["money"]
            p1 = last[1]["observation"]["farms"][1]["money"]
            
            is_loss = "loss" in rpath.lower()
            if is_loss:
                losses += 1
                our_score = min(p0, p1)
                opp_score = max(p0, p1)
                status_str = "LOSS"
            else:
                wins += 1
                our_score = max(p0, p1)
                opp_score = min(p0, p1)
                status_str = "WIN"
                
            margin = our_score - opp_score
            print(f"  [{rel}] Our: ${our_score:,.2f} | Opp: ${opp_score:,.2f} | Status: {status_str} (Margin: ${margin:+,.2f})")
        except Exception as e:
            pass
            
    print(f"\n====================================================")
    print(f"SUMMARY OF ALL DISSECTED REPLAYS:")
    print(f"  Total Replays Analyzed: {len(all_replays)}")
    print(f"  Total Wins: {wins}")
    print(f"  Total Narrow Losses: {losses}")
    if wins + losses > 0:
        print(f"  Win Rate: {wins / (wins + losses) * 100:.1f}%")
    print(f"====================================================")

if __name__ == "__main__":
    main()
