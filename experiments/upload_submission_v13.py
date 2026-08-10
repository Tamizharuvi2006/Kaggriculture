"""Kaggle Direct API Upload Script using Bearer Access Token.

Uploads submission_candidate_competitive_hybrid_v13.py (SHA256: f3f1e1e65b55...) to Lux AI Season 3 competition on Kaggle.
"""

import sys
import os
import json
import urllib.request
import urllib.parse

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
SUBMISSION_FILE = r"D:\kaggriculture\generalization_pipeline\submission_candidate_competitive_hybrid_v13.py"
COMPETITION_NAME = "lux-ai-season-3"
DESCRIPTION = "Competitive Hybrid V13 - Game-Theoretic MPC & Dynamic Meta-Weights (SHA256: f3f1e1e6)"

def upload_to_kaggle():
    print(f"Reading token from {TOKEN_PATH}...", flush=True)
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    filename = os.path.basename(SUBMISSION_FILE)
    file_size = os.path.getsize(SUBMISSION_FILE)
    
    print(f"Requesting upload URL for {filename} ({file_size} bytes)...", flush=True)
    url_req_data = json.dumps({"fileName": filename, "contentLength": file_size, "lastModifiedEpochMs": 0}).encode("utf-8")
    
    req1 = urllib.request.Request(
        f"https://www.kaggle.com/api/v1/competitions/submissions/url/{COMPETITION_NAME}",
        data=url_req_data,
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req1) as resp1:
            resp1_data = json.loads(resp1.read().decode("utf-8"))
            print("Upload URL response:", resp1_data, flush=True)
            upload_url = resp1_data.get("createUrl")
            token_key = resp1_data.get("token")
    except Exception as e:
        print(f"Error requesting upload URL: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

    print(f"Uploading file content to Kaggle storage...", flush=True)
    with open(SUBMISSION_FILE, "rb") as f:
        file_bytes = f.read()

    req2 = urllib.request.Request(
        upload_url,
        data=file_bytes,
        headers={"Content-Type": "application/octet-stream"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req2) as resp2:
            print("File content uploaded successfully!", flush=True)
    except Exception as e:
        print(f"Error uploading file content: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

    print(f"Finalizing submission on Kaggle...", flush=True)
    submit_data = json.dumps({"blobFileKey": token_key, "description": DESCRIPTION}).encode("utf-8")
    req3 = urllib.request.Request(
        f"https://www.kaggle.com/api/v1/competitions/submissions/submit/{COMPETITION_NAME}",
        data=submit_data,
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req3) as resp3:
            resp3_data = json.loads(resp3.read().decode("utf-8"))
            print("\nSUCCESS! Submission Submitted to Kaggle!", flush=True)
            print("Kaggle Submission Result:", json.dumps(resp3_data, indent=2), flush=True)
    except Exception as e:
        print(f"Error finalizing submission: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

if __name__ == "__main__":
    upload_to_kaggle()
