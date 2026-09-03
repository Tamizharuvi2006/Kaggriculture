import subprocess
import json
import urllib.request

url = "https://www.kaggle.com/api/v1/competitions/submissions/list/kaggriculture"
with open(r"C:\Users\aruvi\.kaggle\kaggle.json") as f:
    creds = json.load(f)

req = urllib.request.Request(url)
import base64
auth = base64.b64encode(f"{creds['username']}:{creds['key']}".encode()).decode()
req.add_header("Authorization", f"Basic {auth}")

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

print("Latest 3 Submissions:")
for s in data[:3]:
    print(f"ID: {s.get('id')} | Description: {s.get('description')} | Status: {s.get('status')} | Date: {s.get('date')}")
