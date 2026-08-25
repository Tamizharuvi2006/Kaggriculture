"""
9. Audit Ledger Agent
Maintains an immutable, append-only JSONL log of every experiment lifecycle,
including code hashes, hypothesis, holdout single-shot evaluations, promotion
verdicts, and -- since the memory/genealogy upgrade -- parent lineage,
artifact provenance hashes, market regime tags, and population-level metrics.
"""
import os
import json
import datetime
from typing import Dict, Any


class AuditLedger:
    def __init__(self, ledger_filepath: str = "reports/experiment_ledger.jsonl"):
        self.ledger_filepath = ledger_filepath
        os.makedirs(os.path.dirname(self.ledger_filepath), exist_ok=True)

    def append_record(
        self,
        experiment_id: str,
        baseline_id: str,
        candidate_meta: Dict[str, Any],
        hypothesis_spec: Dict[str, Any],
        exact_replay_res: Dict[str, Any],
        historical_res: Dict[str, Any],
        holdout_res: Dict[str, Any],
        judge_verdict: Dict[str, Any],
        promoted: bool = False,
        parent_exp_id: str = None,
        provenance: Dict[str, str] = None,
        regime_tags: list = None,
        priority_score: float = None,
        population_metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Appends a complete, auditable experiment record to the ledger."""
        record = {
            "experiment_id": experiment_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "baseline_id": baseline_id,
            "candidate_file": candidate_meta.get("candidate_file"),
            "candidate_hash": candidate_meta.get("candidate_hash"),
            "variable_family": hypothesis_spec.get("variable_family"),
            "target_archetype": hypothesis_spec.get("target_archetype"),
            "hypothesis": hypothesis_spec.get("mechanism_hypothesis"),
            "parent_exp_id": parent_exp_id,
            "gate_outcome": judge_verdict.get("verdict"),
            "holdout_suite": holdout_res.get("holdout_suite", "HOLDOUT_V1_N100"),
            "evaluation_mode": "SINGLE_SHOT",
            "results": {
                "win_rate_delta": judge_verdict.get("metrics", {}).get("wr_delta"),
                "mean_mcv_delta": judge_verdict.get("metrics", {}).get("mcv_delta"),
                "tail_p05_delta": judge_verdict.get("metrics", {}).get("tail_p05_delta"),
                "std_ratio": judge_verdict.get("metrics", {}).get("std_ratio"),
                "max_pass_turns": judge_verdict.get("metrics", {}).get("max_pass_turns")
            },
            "gate_outcomes": {
                "gate_1_exact_replay": exact_replay_res.get("status"),
                "gate_2_historical_suite": historical_res.get("status"),
                "gate_3_frozen_holdout": "COMPLETED",
                "gate_4_statistical_judge": judge_verdict.get("verdict")
            },
            "failed_reasons": judge_verdict.get("failed_reasons", []),
            "promoted_to_submission": promoted
        }

        # Provenance: code/config/holdout/result hashes (ArtifactHasher bundle)
        if provenance:
            record["provenance"] = provenance

        # Market regime tags observed during the motivating telemetry
        if regime_tags:
            record["regime_tags"] = regime_tags

        # Priority engine score of the attacked archetype
        if priority_score is not None:
            record["priority_score"] = priority_score

        # Population-level distribution metrics of the holdout run
        if population_metrics:
            record["population_metrics"] = population_metrics

        with open(self.ledger_filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record