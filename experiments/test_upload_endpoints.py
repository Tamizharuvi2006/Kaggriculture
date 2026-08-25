"""Test upload URL endpoints for kaggriculture."""
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

endpoints = [
    "https://www.kaggle.com/api/v1/competitions/submissions/url/kaggriculture",
    "https://www.kaggle.com/api/v1/competitions/kaggriculture/submissions/url",
    "https://www.kaggle.com/api/v1/datasets/upload/file",
    "https://www.kaggle.com/api/i/competitions.SubmissionService/CreateInboundFileSubmissionUrl",
    "https://www.kaggle.com/api/i/competitions.SubmissionService/CreateInboundFileSubmission",
    "https://www.kaggle.com/api/i/inbound.BlobService/CreateInboundResumableUploadUrl",
    "https://www.kaggle.com/api/i/blobs.BlobService/CreateBlob",
    "https://www.kaggle.com/api/i/blobs.BlobService/CreateUploadUrl",
]

payload = json.dumps({"fileName": "submission.py", "contentLength": 312010, "lastModifiedEpochMs": 0}).encode("utf-8")

for ep in endpoints:
    print(f"\nTesting POST to: {ep}")
    req = urllib.request.Request(ep, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  -> SUCCESS! Response: {data}")
    except urllib.error.HTTPError as e:
        print(f"  -> HTTP {e.code}: {e.reason}")
        try:
            print("     Body:", e.read().decode("utf-8")[:150])
        except Exception:
            pass
    except Exception as e:
        print(f"  -> Error: {e}")
