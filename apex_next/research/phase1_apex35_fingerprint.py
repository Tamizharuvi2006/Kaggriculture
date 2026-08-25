"""
PHASE 1: Establish the APEX 3.5 empirical fingerprint (research cycle #1)
Phase 2: Highest-value weakness via real-data priority ranking.

Builds the immutable empirical baseline snapshot for the current production
agent from REAL telemetry, so every future experiment has a reference point:

  - artifact provenance (code/config hashes of submission.py)
  - contract benchmark numbers
  - MCV / WR / tail distributions (86 real trajectories)
  - per-regime performance (RegimeDetector on real data)
  - live ladder snapshot (807 real matches, per submission ref)
  - seat asymmetry breakdown
  - priority-engine ranking of the real failure clusters

Outputs: apex_next/research/APEX35_FINGERPRINT.json
"""
import sys
import os
import io
import json
import ast
import datetime
import numpy as np

_APEX_NEXT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_APEX_NEXT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apex_next.lab.artifact_hasher import ArtifactHasher
from apex_next.lab.regime_detector import RegimeDetector
from apex_next.lab.priority_engine import PriorityEngine
from apex_next.lab.telemetry_ingestor import TelemetryIngestor


PROJECT_ROOT = _PROJECT_ROOT
SUBMISSION_PATH = os.path.join(PROJECT_ROOT, "submission.py")
MCV_DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "replay", "mcv_replay_dataset.json")
OUTPUT_PATH = os.path.join(_APEX_NEXT_ROOT, "research", "APEX35_FINGERPRINT.json")


def extract_default_strategy_config(submission_path):
    """Extracts the DEFAULT_STRATEGY dict literal from submission.py via AST."""
    with io.open(submission_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEFAULT_STRATEGY":
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


def build_fingerprint():
    hasher = ArtifactHasher()
    detector = RegimeDetector()
    priority = PriorityEngine()
    ingestor = TelemetryIngestor()

    fingerprint = {
        "baseline_id": "APEX-3.5-PROD",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "generator": "apex_next/research/phase1_apex35_fingerprint.py",
    }

    # ---- 1. Artifact provenance of the production agent ----
    config = extract_default_strategy_config(SUBMISSION_PATH)
    fingerprint["artifacts"] = {
        "code_hash": hasher.hash_file(SUBMISSION_PATH),
        "config_hash": hasher.hash_config(config) if config else None,
        "config_keys": sorted(config.keys()) if config else None,
        "documented_candidate_hash_apex35": "78738c1b",
    }

    # ---- 2. Contract benchmark numbers (BASELINE_CONTRACT.md) ----
    fingerprint["contract_benchmarks"] = {
        "known_ladder_elo": "~1650-1700",
        "benchmark_win_rate_vs_v41": 0.792,
        "mean_final_mcv": 142850,
        "p05_tail_mcv": 98400,
        "p95_peak_mcv": 189200,
        "avg_step_latency_ms": 12.4,
        "max_step_latency_ms": 85.0,
        "pass_action_rate": 0.008,
    }

    # ---- 3. MCV/WR distribution from the real 86-trajectory dataset ----
    rows = detector.load_real_dataset(MCV_DATASET_PATH)
    trajectories = {}
    for r in rows:
        key = (r.get("file"), r.get("player_idx"))
        trajectories.setdefault(key, []).append(r)

    mcvs = np.array([t[-1].get("final_wealth", 0.0) for t in trajectories.values()])
    wins = sum(1 for t in trajectories.values() if t[-1].get("won_match"))
    fingerprint["mcv_population"] = {
        "n_trajectories": len(trajectories),
        "win_rate": round(wins / len(trajectories), 4),
        "mean_mcv": round(float(np.mean(mcvs)), 1),
        "std_mcv": round(float(np.std(mcvs)), 1),
        "p05_mcv": round(float(np.percentile(mcvs, 5)), 1),
        "p10_mcv": round(float(np.percentile(mcvs, 10)), 1),
        "median_mcv": round(float(np.percentile(mcvs, 50)), 1),
        "p90_mcv": round(float(np.percentile(mcvs, 90)), 1),
        "p95_mcv": round(float(np.percentile(mcvs, 95)), 1),
    }

    # ---- 4. Regime breakdown (the actionable weakness map) ----
    regime_map = detector.evaluate_by_regime(rows)
    fingerprint["regime_performance"] = regime_map["by_regime"]
    fingerprint["weakest_regime"] = {
        "regime": regime_map["weakest_regime"],
        "win_rate": regime_map["weakest_win_rate"],
        "diagnosis": regime_map["diagnosis"],
    }

    # ---- 5. Live ladder snapshot (807 real matches, per submission ref) ----
    import re
    live = ingestor.ingest_live_telemetry()
    per_ref = {}
    for m in live:
        match = re.search(r"submission_(\d+)_episodes", m["filepath"])
        ref = match.group(1) if match else "unknown"
        bucket = per_ref.setdefault(ref, {"matches": 0, "wins": 0, "losses": 0,
                                          "mcvs": [], "elo_deltas": [], "seat0_wins": 0, "seat0_n": 0,
                                          "seat1_wins": 0, "seat1_n": 0})
        bucket["matches"] += 1
        if m["result"] == "WIN":
            bucket["wins"] += 1
        elif m["result"] == "LOSS":
            bucket["losses"] += 1
        bucket["mcvs"].append(m["our_mcv"])
        bucket["elo_deltas"].append(m.get("our_elo_delta", 0.0))
        if m["seat"] == 0:
            bucket["seat0_n"] += 1
            bucket["seat0_wins"] += int(m["result"] == "WIN")
        else:
            bucket["seat1_n"] += 1
            bucket["seat1_wins"] += int(m["result"] == "WIN")

    live_snapshot = {}
    for ref, b in per_ref.items():
        arr = np.array(b["mcvs"])
        live_snapshot[ref] = {
            "matches": b["matches"],
            "win_rate": round(b["wins"] / b["matches"], 4),
            "mean_mcv": round(float(np.mean(arr)), 1),
            "mean_elo_delta": round(float(np.mean(b["elo_deltas"])), 3),
            "seat0_win_rate": round(b["seat0_wins"] / b["seat0_n"], 4) if b["seat0_n"] else None,
            "seat1_win_rate": round(b["seat1_wins"] / b["seat1_n"], 4) if b["seat1_n"] else None,
        }
    total_wins = sum(b["wins"] for b in per_ref.values())
    total_matches = sum(b["matches"] for b in per_ref.values())
    fingerprint["live_ladder"] = {
        "total_matches": total_matches,
        "overall_win_rate": round(total_wins / total_matches, 4),
        "by_submission_ref": live_snapshot,
    }

    # ---- 6. Phase 2: priority ranking of REAL failure clusters ----
    # Frequency = share of LOSSES per regime in the real population.
    regime_stats = regime_map["by_regime"]
    total_losses = sum(
        round(s["matches"] * (1 - s["win_rate"])) for s in regime_stats.values()
        if s.get("matches", 0) > 0
    )
    clusters = []
    for regime, s in regime_stats.items():
        if s.get("matches", 0) == 0:
            continue
        losses = round(s["matches"] * (1 - s["win_rate"]))
        clusters.append({
            "archetype": regime,
            "frequency": losses / total_losses if total_losses else 0.0,
            "impact": 1.0 - s["win_rate"],   # higher loss rate = higher impact
            "confidence": min(1.0, s["matches"] / 40.0),  # more evidence = more confidence
            "fixability": 0.6,               # one-variable market-timing fixes are tractable
        })
    ranking = priority.rank_clusters(clusters)
    fingerprint["priority_ranking"] = {
        "total_clusters": ranking["total_clusters"],
        "selected_archetype": ranking["selected_archetype"],
        "selected_priority": ranking["selected_priority"],
        "ranking": ranking["ranking"],
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with io.open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(fingerprint, f, indent=2)
    return fingerprint


if __name__ == "__main__":
    fp = build_fingerprint()
    print("=== APEX 3.5 FINGERPRINT ===")
    print("code_hash:", fp["artifacts"]["code_hash"][:16])
    print("config_hash:", (fp["artifacts"]["config_hash"] or "N/A")[:16])
    print("MCV population:", fp["mcv_population"])
    print("Weakest regime:", fp["weakest_regime"])
    print("Live ladder:", fp["live_ladder"]["total_matches"], "matches, WR",
          fp["live_ladder"]["overall_win_rate"])
    print("PRIORITY SELECTION:", fp["priority_ranking"]["selected_archetype"],
          f"({fp['priority_ranking']['selected_priority']})")
    for r in fp["priority_ranking"]["ranking"]:
        print(f"  {r['archetype']:<20} freq={r['frequency']:.3f} impact={r['impact']:.3f} "
              f"conf={r['confidence']:.3f} score={r['penalized_score']}")
    print("\nSaved:", OUTPUT_PATH)
