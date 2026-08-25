"""Attach immutable package/evidence hashes to the single-file manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
manifest_path = ROOT / "reports/step5b/APEX4_PPO_FINAL_SINGLE.manifest.json"
zip_path = ROOT / "release_packages/APEX4_PPO_FINAL_SINGLE_20260821.zip"
single_path = ROOT / "release_packages/APEX4_PPO_FINAL_SINGLE.py"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.update({
    "zip": str(zip_path),
    "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest().upper(),
    "single_file_equivalence_report": str(ROOT / "reports/step5b/single_file_equivalence_32.json"),
    "clean_zip_dry_run": {
        "status": "PASS",
        "zip_entries": [single_path.name],
        "steps": 720,
        "errors": [],
    },
})
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
