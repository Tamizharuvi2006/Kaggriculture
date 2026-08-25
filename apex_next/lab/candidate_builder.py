"""
4. Candidate Builder
Constructs an isolated candidate branch in `experiments/EXP-XXXX/` without touching the immutable baseline.
Calculates SHA-256 code hash and sets up local evaluation artifacts.
"""
import os
import shutil
import hashlib
import json
from typing import Dict, Any


class CandidateBuilder:
    def __init__(self, base_experiments_dir: str = "experiments"):
        self.base_experiments_dir = base_experiments_dir

    def calculate_sha256(self, filepath: str) -> str:
        """Calculates SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_candidate_branch(
        self,
        hypothesis_spec: Dict[str, Any],
        baseline_file: str,
        candidate_code_content: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Creates an isolated candidate folder with candidate code, metadata, and hash."""
        exp_id = hypothesis_spec["experiment_id"]
        exp_dir = os.path.join(self.base_experiments_dir, exp_id)
        os.makedirs(exp_dir, exist_ok=True)

        candidate_file = os.path.join(exp_dir, "candidate_agent.py")
        with open(candidate_file, "w", encoding="utf-8") as f:
            f.write(candidate_code_content)

        code_hash = self.calculate_sha256(candidate_file)

        metadata = {
            "experiment_id": exp_id,
            "baseline_source": baseline_file,
            "baseline_hash": self.calculate_sha256(baseline_file) if os.path.exists(baseline_file) else "N/A",
            "candidate_file": candidate_file,
            "candidate_hash": code_hash,
            "hypothesis": hypothesis_spec,
            "config": config or {},
            "status": "BUILT"
        }

        with open(os.path.join(exp_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        with open(os.path.join(exp_dir, "hypothesis.md"), "w", encoding="utf-8") as f:
            f.write(f"# Hypothesis for {exp_id}\n\n")
            f.write(f"- **Target Archetype:** {hypothesis_spec['target_archetype']}\n")
            f.write(f"- **Variable Family:** {hypothesis_spec['variable_family']}\n")
            f.write(f"- **Mechanism:** {hypothesis_spec['mechanism_hypothesis']}\n")
            f.write(f"- **Candidate SHA256:** `{code_hash}`\n")

        return metadata
