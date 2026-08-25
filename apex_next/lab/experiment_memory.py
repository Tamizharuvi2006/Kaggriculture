"""
11. Experiment Memory (Hypothesis Memory + Experiment Genealogy)
Research memory, not just logging. Before a new hypothesis is generated, the
memory is searched to answer: "Have we already tried this?" Every experiment
records its parent so the lineage of a failure archetype can be reconstructed
(EXP-0110 -> EXP-0111 -> EXP-0112 -> ...) instead of a flat list of dead ends.
"""
import os
import re
import json
from typing import Dict, Any, List, Optional


class ExperimentMemory:
    """Append-only read model over the audit ledger. Never mutates the ledger."""

    def __init__(self, ledger_filepath: str = "reports/experiment_ledger.jsonl"):
        self.ledger_filepath = ledger_filepath

    def load_records(self) -> List[Dict[str, Any]]:
        """Loads every ledger record, oldest first."""
        if not os.path.exists(self.ledger_filepath):
            return []
        records = []
        with open(self.ledger_filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    @staticmethod
    def _tokens(mechanism: str) -> set:
        """Lower-cased alphanumeric token set of a mechanism description."""
        return set(re.findall(r"[a-z0-9]+", mechanism.lower()))

    def search_hypothesis(
        self,
        variable_family: Optional[str] = None,
        target_archetype: Optional[str] = None,
        mechanism: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Searches experiment memory for prior attempts on the same problem.

        Returns a lookup verdict: either the problem is novel ("GENERATE") or
        it has been tried before ("LEARN") with the ranked prior evidence.
        """
        records = self.load_records()
        if not records:
            return {"verdict": "GENERATE", "prior_attempts": [], "reasons": ["No experiment history yet."]}

        scored = []
        query_tokens = self._tokens(mechanism or "")

        for rec in records:
            score = 0.0
            match_reasons = []

            if variable_family and rec.get("variable_family") == variable_family:
                score += 2.0
                match_reasons.append("variable_family")

            if target_archetype:
                if rec.get("target_archetype") == target_archetype:
                    score += 2.0
                    match_reasons.append("target_archetype")
                elif target_archetype in (rec.get("target_archetype") or ""):
                    score += 1.0
                    match_reasons.append("archetype_keyword")

            if query_tokens and rec.get("hypothesis"):
                rec_tokens = self._tokens(rec["hypothesis"])
                overlap = len(query_tokens & rec_tokens)
                if overlap:
                    score += min(3.0, overlap * 0.75)
                    match_reasons.append(f"mechanism_tokens={overlap}")

            if score > 0:
                scored.append({
                    "experiment_id": rec["experiment_id"],
                    "score": round(score, 2),
                    "match_reasons": match_reasons,
                    "gate_outcome": rec.get("gate_outcome", rec.get("gate_outcomes", {}).get("gate_4_statistical_judge")),
                    "promoted_to_submission": rec.get("promoted_to_submission", False),
                    "hypothesis": rec.get("hypothesis"),
                    "results": rec.get("results", {})
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        prior_attempts = scored[:top_k]

        # A hypothesis family that has already been attempted and falsified is a
        # strong signal to learn instead of re-running the same dead end.
        strong_prior = any(
            a["score"] >= 4.0 and not a["promoted_to_submission"] and
            a.get("gate_outcome") in ("FALSIFIED_REJECTED", "FALSIFIED_GATE_1",
                                      "FALSIFIED_GATE_2", "FALSIFIED_GATE_3")
            for a in prior_attempts
        )

        return {
            "verdict": "LEARN" if strong_prior else "GENERATE",
            "prior_attempts": prior_attempts,
            "reasons": [
                "Falsified attempt with >=4.0 similarity already exists in memory."
            ] if strong_prior else ["No falsified attempt with sufficient similarity."]
        }

    def assign_parent(self, variable_family: str, target_archetype: Optional[str] = None) -> Optional[str]:
        """
        Assigns the most recent experiment in the same (family, archetype) lineage
        as the parent, so the genealogy graph grows instead of flattening.
        """
        records = self.load_records()
        lineage_candidates = [
            rec for rec in records
            if rec.get("variable_family") == variable_family
            and (target_archetype is None or rec.get("target_archetype") == target_archetype)
        ]
        if not lineage_candidates:
            return None
        lineage_candidates.sort(key=lambda r: r.get("timestamp", ""))
        return lineage_candidates[-1]["experiment_id"]

    def genealogy_tree(self) -> Dict[str, Any]:
        """Reconstructs the full lineage forest from parent pointers."""
        records = self.load_records()
        nodes = {}
        for rec in records:
            exp_id = rec["experiment_id"]
            nodes[exp_id] = {
                "experiment_id": exp_id,
                "parent": rec.get("parent_exp_id"),
                "variable_family": rec.get("variable_family"),
                "target_archetype": rec.get("target_archetype"),
                "gate_outcome": rec.get("gate_outcome", rec.get("gate_outcomes", {}).get("gate_4_statistical_judge")),
                "promoted_to_submission": rec.get("promoted_to_submission", False),
                "children": []
            }

        roots = []
        for node in nodes.values():
            parent_id = node["parent"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node["experiment_id"])
            else:
                roots.append(node["experiment_id"])

        return {
            "total_experiments": len(nodes),
            "roots": roots,
            "nodes": nodes,
            "lineages": [self._lineage_to_string(nodes, root) for root in roots]
        }

    @staticmethod
    def _lineage_to_string(nodes: Dict[str, Any], root_id: str, depth: int = 0) -> str:
        node = nodes[root_id]
        outcome = "PASS" if node["promoted_to_submission"] else "FAILED"
        line = "   " * depth + f"{node['experiment_id']} ({outcome})"
        child_lines = [ExperimentMemory._lineage_to_string(nodes, c, depth + 1) for c in node["children"]]
        return "\n".join([line] + child_lines) if child_lines else line

    def lineage_of(self, experiment_id: str) -> List[str]:
        """Returns the ancestor chain (oldest first) for a given experiment."""
        records = {r["experiment_id"]: r for r in self.load_records()}
        chain = []
        current = records.get(experiment_id)
        seen = set()
        while current is not None and current["experiment_id"] not in seen:
            chain.append(current["experiment_id"])
            seen.add(current["experiment_id"])
            current = records.get(current.get("parent_exp_id"))
        chain.reverse()
        return chain

    def attempt_count_for_archetype(self, target_archetype: Optional[str] = None,
                                     variable_family: Optional[str] = None) -> int:
        """How many times have we already attacked this failure archetype?"""
        records = self.load_records()
        return sum(
            1 for rec in records
            if (target_archetype is None or rec.get("target_archetype") == target_archetype)
            and (variable_family is None or rec.get("variable_family") == variable_family)
        )


if __name__ == "__main__":
    memory = ExperimentMemory()
    lookup = memory.search_hypothesis(
        variable_family="Timing",
        target_archetype="CROP_DRIFT",
        mechanism="Dynamic scheduler will adapt to market swings."
    )
    print("Memory lookup verdict:", lookup["verdict"])
    print("Prior attempts:", len(lookup["prior_attempts"]))
    print("Genealogy:\n", memory.genealogy_tree().get("lineages", ["(empty)"]))