"""Submit Immutable APEX 3.0 Challenger Artifact to Kaggle.

Competition: kaggriculture
File: generalization_pipeline/submission_candidate_apex30.py
Description: APEX 3.0 Challenger - Empirical State-Conditioned MCV (9-Phase Hardened Monolithic Build, SHA256: bac00678)
"""

from __future__ import annotations
import sys
import os
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from kaggle.api.kaggle_api_extended import KaggleApi

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_PATH = os.path.join(BASE_DIR, "generalization_pipeline", "submission_candidate_apex30.py")
EXPECTED_HASH = "bac00678cd9b2acc99e459b89a9d8560c8cce51dc50765381610990cdc37a67a"

def main():
    print("==================================================================================", flush=True)
    print("🚀 SUBMITTING IMMUTABLE APEX 3.0 CHALLENGER TO KAGGLE", flush=True)
    print("==================================================================================", flush=True)

    if not os.path.exists(ART_PATH):
        print(f"ERROR: Artifact file not found at {ART_PATH}")
        sys.exit(1)

    with open(ART_PATH, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    print(f"Artifact File Path : {ART_PATH}")
    print(f"Artifact File Size : {os.path.getsize(ART_PATH):,} bytes")
    print(f"Computed SHA256    : {file_hash}")
    print(f"Expected SHA256    : {EXPECTED_HASH}")

    if file_hash != EXPECTED_HASH:
        print("ERROR: SHA256 Hash Mismatch! Aborting submission to protect candidate integrity!")
        sys.exit(1)

    print("SHA256 Hash Match Verified 100%! Proceeding with Kaggle API submission...", flush=True)

    api = KaggleApi()
    api.authenticate()

    description = "APEX 3.0 Challenger - Empirical State-Conditioned MCV (9-Phase Hardened Monolithic Build, SHA256: bac00678)"
    
    response = api.competition_submit(
        file_name=ART_PATH,
        message=description,
        competition="kaggriculture"
    )

    print("\n----------------------------------------------------------------------------------")
    print("SUBMISSION RESPONSE FROM KAGGLE:")
    print(response)
    print("----------------------------------------------------------------------------------")
    print("APEX 3.0 Challenger successfully submitted to Kaggle! 🏆")
    print("==================================================================================", flush=True)

if __name__ == "__main__":
    main()
