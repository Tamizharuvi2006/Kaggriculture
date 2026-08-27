"""Download metadata files from Hugging Face dataset KiroSamurai/kaggriculture-il."""
import os
import sys
from huggingface_hub import hf_hub_download

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "datasets", "il")
os.makedirs(TARGET_DIR, exist_ok=True)

REPO_ID = "KiroSamurai/kaggriculture-il"
FILES_TO_DOWNLOAD = [
    "datasets/il/index.csv",
    "datasets/il/seats.csv",
    "datasets/il/clusters.csv",
    "datasets/il/frozen.json",
    "bootstrap_v4/calibration_1327_v4.json",
]

def main():
    print(f"Downloading metadata files from {REPO_ID}...")
    for rel_path in FILES_TO_DOWNLOAD:
        try:
            print(f"Downloading {rel_path}...")
            local_path = hf_hub_download(
                repo_id=REPO_ID,
                filename=rel_path,
                repo_type="dataset",
                local_dir=BASE_DIR,
            )
            print(f"  -> Saved to {local_path} ({os.path.getsize(local_path):,} bytes)")
        except Exception as e:
            print(f"  -> Failed to download {rel_path}: {e}")

if __name__ == "__main__":
    main()
