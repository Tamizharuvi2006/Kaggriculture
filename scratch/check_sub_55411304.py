"""Check status of submission 55411304 on Kaggle.
"""

from __future__ import annotations
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    api = KaggleApi()
    api.authenticate()
    subs = api.competition_submissions('kaggriculture')
    s = subs[0]
    
    ref = getattr(s, "_ref", getattr(s, "ref", "N/A"))
    status = getattr(s, "_status", getattr(s, "status", "N/A"))
    score = getattr(s, "_public_score", getattr(s, "publicScore", "N/A"))
    fname = getattr(s, "_file_name", getattr(s, "fileName", "N/A"))
    date = getattr(s, "_date", getattr(s, "date", "N/A"))
    desc = getattr(s, "_description", getattr(s, "description", "N/A"))

    print(f"Latest Kaggle Submission Details:")
    print(f"  ├── Submission Ref ID : {ref}")
    print(f"  ├── Status            : {status}")
    print(f"  ├── Public Score      : {score}")
    print(f"  ├── File Name         : {fname}")
    print(f"  ├── Submission Date   : {date}")
    print(f"  └── Description       : {desc}")

if __name__ == "__main__":
    main()
