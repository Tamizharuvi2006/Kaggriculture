"""
16. Champion Registry (Champion / Challenger Architecture)
Tracks the current champion and the promotion contract between champion and
challenger. The registry is a read-model + write-authority RESTRICTED to the
Release Manager path: only after the statistical judge approves a challenger
does the registry promote it. The registry itself never mutates submission.py.
"""
import os
import json
import datetime
from typing import Dict, Any, Optional


class ChampionRegistry:
    def __init__(self, registry_filepath: str = "reports/champion_registry.json"):
        self.registry_filepath = registry_filepath
        self._ensure_registry()

    def _ensure_registry(self) -> None:
        if not os.path.exists(self.registry_filepath):
            self._write({
                "champion": None,
                "history": [],
                "promotion_rule": "Challenger must pass ALL 6 statistical gates on the frozen holdout.",
                "auto_revert": "DISABLED_BY_CONTRACT"
            })

    def _write(self, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.registry_filepath), exist_ok=True)
        with open(self.registry_filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _read(self) -> Dict[str, Any]:
        with open(self.registry_filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def current_champion(self) -> Optional[Dict[str, Any]]:
        return self._read().get("champion")

    def promote_challenger(
        self,
        challenger_meta: Dict[str, Any],
        judge_verdict: Dict[str, Any],
        holdout_res: Dict[str, Any],
        version_tag: str,
        release_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Promotes a challenger to champion ONLY when:
          1. The statistical judge approved it (promotable).
          2. The Release Manager has confirmed deployment (release_confirmed).
        This encodes "deterministic release controller owns the write" -- the
        registry is a bookkeeper, never an initiator.
        """
        if not judge_verdict.get("promotable"):
            return {"status": "REJECTED", "reason": "Challenger failed statistical judge gate."}
        if not release_confirmed:
            return {"status": "PENDING_DEPLOYMENT", "reason": "Release Manager has not confirmed deployment."}

        registry = self._read()
        old_champion = registry.get("champion")

        new_champion = {
            "version_tag": version_tag,
            "candidate_file": challenger_meta.get("candidate_file"),
            "candidate_hash": challenger_meta.get("candidate_hash"),
            "baseline_hash": challenger_meta.get("baseline_hash"),
            "holdout_suite": holdout_res.get("holdout_suite"),
            "holdout_hash": holdout_res.get("holdout_hash"),
            "win_rate": holdout_res.get("win_rate"),
            "mean_mcv": holdout_res.get("candidate_mean_mcv"),
            "p05_mcv": holdout_res.get("candidate_p05_mcv"),
            "promoted_at": datetime.datetime.utcnow().isoformat() + "Z",
            "judge_verdict": judge_verdict.get("verdict")
        }

        registry["history"].append({
            "from": old_champion["version_tag"] if old_champion else None,
            "to": version_tag,
            "candidate_hash": challenger_meta.get("candidate_hash"),
            "promoted_at": new_champion["promoted_at"]
        })
        registry["champion"] = new_champion
        self._write(registry)

        return {"status": "PROMOTED", "champion": new_champion}


if __name__ == "__main__":
    registry = ChampionRegistry(registry_filepath="reports/champion_registry_test.json")
    print("Current champion:", registry.current_champion())
    print("Promote without judge approval:",
          registry.promote_challenger({}, {"promotable": False}, {}, "APEX-3.6")["status"])