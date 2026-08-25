"""
10. Release Manager (Deployment Authority)
Only this component has write authority to prepare a Kaggle submission.
Performs AST/syntax validation, archives old production, and outputs submission.py.
"""
import os
import shutil
import ast
import datetime
from typing import Dict, Any


class ReleaseManager:
    def __init__(
        self,
        submission_target: str = "submission.py",
        archive_dir: str = "baseline/archive"
    ):
        self.submission_target = submission_target
        self.archive_dir = archive_dir
        os.makedirs(self.archive_dir, exist_ok=True)

    def validate_code_syntax(self, code_filepath: str) -> bool:
        """Verifies python code compiles cleanly via AST parsing."""
        try:
            with open(code_filepath, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source)
            return True
        except Exception as e:
            print(f"[ReleaseManager] Syntax validation failed: {e}")
            return False

    def prepare_release(
        self,
        candidate_meta: Dict[str, Any],
        judge_verdict: Dict[str, Any],
        new_version_tag: str = "APEX-3.6-PROD"
    ) -> Dict[str, Any]:
        """Prepares a single submission package only after statistical gate clearance."""
        if not judge_verdict.get("promotable"):
            return {
                "status": "REJECTED",
                "reason": "Candidate did not pass statistical judge gate."
            }

        candidate_file = candidate_meta.get("candidate_file")
        if not candidate_file or not os.path.exists(candidate_file):
            return {
                "status": "FAILED",
                "reason": f"Candidate file {candidate_file} not found."
            }

        if not self.validate_code_syntax(candidate_file):
            return {
                "status": "FAILED",
                "reason": "Candidate code contains syntax or AST parsing errors."
            }

        # 1. Archive current active production if it exists
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if os.path.exists(self.submission_target):
            archive_target = os.path.join(self.archive_dir, f"submission_pre_{new_version_tag}_{timestamp}.py")
            shutil.copy2(self.submission_target, archive_target)
            print(f"[ReleaseManager] Archived existing production to {archive_target}")

        # 2. Deploy candidate to submission.py
        shutil.copy2(candidate_file, self.submission_target)
        print(f"[ReleaseManager] Promoted {candidate_file} to {self.submission_target} as {new_version_tag}")

        return {
            "status": "RELEASE_READY",
            "version_tag": new_version_tag,
            "submission_path": os.path.abspath(self.submission_target),
            "candidate_hash": candidate_meta.get("candidate_hash"),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
