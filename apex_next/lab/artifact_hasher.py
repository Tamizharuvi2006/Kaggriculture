"""
14. Artifact Hasher (Provenance / Artifact Immutability)
Hashes every artifact that participates in an experiment so any ledger record
can prove: "this result came from exactly this code, with exactly this config,
against exactly this holdout." No artifact hash means no provenance.
"""
import os
import json
import hashlib
from typing import Dict, Any, List, Optional


class ArtifactHasher:
    @staticmethod
    def hash_file(filepath: str) -> Optional[str]:
        """SHA-256 of a file's bytes; None if the file does not exist."""
        if not os.path.exists(filepath):
            return None
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        return ArtifactHasher.hash_bytes(text.encode("utf-8"))

    @staticmethod
    def hash_config(config: Dict[str, Any]) -> str:
        """Deterministic canonical-JSON hash of a config dict (sorted keys)."""
        canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
        return ArtifactHasher.hash_text(canonical)

    @staticmethod
    def hash_seed_list(seeds: List[int]) -> str:
        return ArtifactHasher.hash_text(",".join(str(s) for s in seeds))

    @staticmethod
    def hash_metrics(metrics: Dict[str, Any]) -> str:
        canonical = json.dumps(metrics, sort_keys=True, separators=(",", ":"), default=str)
        return ArtifactHasher.hash_text(canonical)

    def build_provenance(
        self,
        candidate_file: str,
        baseline_file: str,
        config: Dict[str, Any],
        holdout_seeds: List[int],
        results: Dict[str, Any]
    ) -> Dict[str, str]:
        """Builds the full artifact hash bundle for a ledger record."""
        return {
            "code_hash": self.hash_file(candidate_file),
            "baseline_hash": self.hash_file(baseline_file),
            "config_hash": self.hash_config(config),
            "holdout_hash": self.hash_seed_list(sorted(set(holdout_seeds))),
            "result_hash": self.hash_metrics(results)
        }


if __name__ == "__main__":
    hasher = ArtifactHasher()
    prov = hasher.build_provenance("submission.py", "submission.py", {"hands": 13}, [1000, 1037], {"wr": 0.79})
    print("Provenance bundle:", prov)