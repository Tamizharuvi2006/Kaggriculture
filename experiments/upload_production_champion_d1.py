"""Kaggle Direct API Upload Script using Bearer Access Token.
Uploads D:\kaggriculture\submission.py (Variant D.1 Production Champion) directly to Kaggle.
"""

from __future__ import annotations
import sys
import os
import json
import ast
import hashlib
import urllib.request
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN_PATH = r"C:\Users\aruvi\.kaggle\access_token"
SUBMISSION_FILE = r"D:\kaggriculture\submission.py"
COMPETITION_NAME = "kaggriculture"

def upload_production_champion():
    print("=" * 100, flush=True)
    print("SUBMITTING VARIANT D.1 PRODUCTION CHAMPION TO KAGGLE", flush=True)
    print("=" * 100, flush=True)

    if not os.path.exists(SUBMISSION_FILE):
        print(f"ERROR: Submission file not found at {SUBMISSION_FILE}")
        sys.exit(1)

    # 1. AST Validation Check
    with open(SUBMISSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        ast.parse(content)
        print("✅ AST Syntax Check: 100% Valid & Clean Python!")
    except Exception as e:
        print(f"❌ AST Syntax Error: {e}")
        sys.exit(1)

    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    file_size = len(content.encode("utf-8"))
    description = f"Variant D.1 Production Champion (3Q/38-Straw/8-Cow/13-Worker, 86% Universal Loss Rescue, Step 696 Buffer, SHA256: {file_hash[:8]})"

    print(f"Submission File Path : {SUBMISSION_FILE}")
    print(f"Submission File Size : {file_size:,} bytes")
    print(f"Computed SHA256      : {file_hash}")
    print(f"Submission Message   : {description}\n")

    print(f"Reading token from {TOKEN_PATH}...", flush=True)
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    filename = os.path.basename(SUBMISSION_FILE)

    print(f"1. Requesting upload URL for {filename} ({file_size} bytes)...", flush=True)
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
            print("  -> Upload URL received successfully!", flush=True)
            upload_url = resp1_data.get("createUrl")
            token_key = resp1_data.get("token")
    except Exception as e:
        print(f"Error requesting upload URL: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

    print("2. Uploading standalone submission file content to Kaggle storage...", flush=True)
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
            print("  -> File content uploaded successfully!", flush=True)
    except Exception as e:
        print(f"Error uploading file content: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

    print("3. Finalizing submission on Kaggle...", flush=True)
    submit_data = json.dumps({"blobFileKey": token_key, "description": description}).encode("utf-8")
    req3 = urllib.request.Request(
        f"https://www.kaggle.com/api/v1/competitions/submissions/submit/{COMPETITION_NAME}",
        data=submit_data,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req3) as resp3:
            resp3_data = json.loads(resp3.read().decode("utf-8"))
            print("\n" + "=" * 100, flush=True)
            print("🎉 SUCCESS! VARIANT D.1 OFFICIALLY SUBMITTED TO KAGGLE!", flush=True)
            print("Kaggle Submission Ref/Result:", json.dumps(resp3_data, indent=2), flush=True)
            print("=" * 100, flush=True)
    except Exception as e:
        print(f"Error finalizing submission: {e}", flush=True)
        if hasattr(e, "read"):
            print("Error body:", e.read().decode("utf-8"))
        sys.exit(1)

if __name__ == "__main__":
    upload_production_champion()
