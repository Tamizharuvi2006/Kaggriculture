"""Forensic decision logging and post-match audit tracker."""
from __future__ import annotations
import json
import os
from typing import Dict, Any, List, Optional
from engine.strategy.scarcity_pivot import ScarcityDecision

class ForensicLogger:
    """Collects and serializes forensic decision traces for each match step."""
    def __init__(self, match_id: Optional[str] = None):
        self.match_id = match_id or "match_forensic"
        self.traces: List[Dict[str, Any]] = []

    def log_decision(self, step: int, decision: ScarcityDecision, executed_action: Dict[str, Any]):
        entry = {
            "step": step,
            "day": step // 24,
            "hour": step % 24,
            "chosen_crop": decision.chosen_crop,
            "expected_terminal_value": round(decision.expected_terminal_value, 1),
            "alternatives": {k: round(v, 1) for k, v in decision.alternatives.items()},
            "solvency": decision.solvency_status,
            "reason": decision.decision_reason,
            "executed_action": executed_action,
        }
        self.traces.append(entry)

    def export_jsonl(self, filepath: str):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for t in self.traces:
                f.write(json.dumps(t) + "\n")

    def export_summary_md(self, filepath: str):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# 🔬 Forensic Match Audit ({self.match_id})\n\n")
            f.write(f"Total Steps Logged: {len(self.traces)}\n\n")
            f.write("## Key Strategic Pivots & Decisions\n\n")
            
            pivots = [t for t in self.traces if not t["reason"].startswith("BASELINE")]
            if not pivots:
                f.write("No scarcity pivots triggered; baseline executed throughout match.\n")
            else:
                for p in pivots:
                    f.write(f"### Turn {p['step']} (Day {p['day']}, Hour {p['hour']}): {p['chosen_crop']}\n")
                    f.write(f"- **Expected Terminal Net**: +${p['expected_terminal_value']:,.0f}\n")
                    f.write(f"- **Reason**: `{p['reason']}`\n")
                    f.write(f"- **Alternatives**: {p['alternatives']}\n\n")
