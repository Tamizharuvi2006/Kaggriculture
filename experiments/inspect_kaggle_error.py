"""Kaggle API Authorization & 403 Response Inspector.

Inspects the detailed Kaggle API error response, headers, and body for CreateSubmission to determine the exact server-side authorization status.
"""

import sys
import os
import json
from kaggle.api.kaggle_api_extended import KaggleApi

COMPETITION_NAME = "lux-ai-season-3"
SUBMISSION_FILE = r"D:\kaggriculture\generalization_pipeline\submission_candidate_competitive_hybrid_v13.py"

def inspect_error():
    print("Initializing Kaggle API and authenticating...", flush=True)
    api = KaggleApi()
    api.authenticate()
    
    print(f"Authenticated Kaggle User: {getattr(api, 'username', 'Unknown')}", flush=True)
    
    try:
        print(f"Attempting API competition_submit for '{COMPETITION_NAME}'...", flush=True)
        res = api.competition_submit(SUBMISSION_FILE, "Competitive Hybrid V13 Inspection", COMPETITION_NAME)
        print("Submit API Response:", res, flush=True)
    except Exception as e:
        print("\n--- KAGGLE API DETAILED ERROR DIAGNOSTIC ---", flush=True)
        print("Error Type:", type(e).__name__, flush=True)
        print("Error Message:", str(e), flush=True)
        
        if hasattr(e, "response") and e.response is not None:
            print("HTTP Status Code:", e.response.status_code, flush=True)
            print("HTTP Response Headers:", dict(e.response.headers), flush=True)
            print("HTTP Response Text Body:", e.response.text, flush=True)
        else:
            print("No HTTP response object attached to exception.", flush=True)

if __name__ == "__main__":
    inspect_error()
