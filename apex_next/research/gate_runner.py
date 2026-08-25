"""Gate runner for contract-compliant research cycles.

Executes the 4-gate falsification pipeline using the real paired match runner:

  Gate 1  Exact Replay       46 real ladder loss seeds (apex33_loss_seeds_cache)
                              pass rule: candidate WR >= 60% vs baseline
  Gate 2  Historical Suite   50 fixed multi-archetype seeds (10 groups x 5)
                              pass rule: overall >= 75% AND no group < 60%
  Gate 3  Frozen Holdout     HOLDOUT_V1_N100, single shot, never re-run
  Gate 4  Statistical Judge  6 dimensions, verdict + ledger + registry

Run from D:\\Kaggriculture:
  python apex_next/research/gate_runner.py EXP-0115 D:\\...\\EXP-0115
"""
import argparse
import hashlib
import json
import os
import random
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "apex_next"))

from apex_next.lab.audit_ledger import AuditLedger
from apex_next.lab.champion_registry import ChampionRegistry
from apex_next.research.match_runner import run_paired, summarize

MAX_WORKERS = 4

parser = argparse.ArgumentParser()
parser.add_argument("exp_id", help="experiment id, e.g. EXP-0115")
parser.add_argument("exp_dir", help="experiment directory, e.g. apex_next/research/EXP-0115")
args = parser.parse_args()

EXP_ID = args.exp_id
EXP_DIR = args.exp_dir if os.path.isabs(args.exp_dir) else os.path.join(_PROJECT_ROOT, args.exp_dir)
SEEDS_DIR = os.path.join(EXP_DIR, "seeds")
RESULTS_DIR = os.path.join(EXP_DIR, "results")
CANDIDATE_FILE = os.path.join(EXP_DIR, "candidate", "candidate_submission.py")
LOSS_SEEDS_CACHE = os.path.join(_PROJECT_ROOT, "reports", "live_match_telemetry", "apex33_loss_seeds_cache.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_seeds(path, required=True):
    if not os.path.exists(path):
        if required:
            raise FileNotFoundError(path)
        return []
    return json.load(open(path, encoding="utf-8"))


def save_seeds(path, seeds, master_seed, purpose):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "purpose": purpose,
        "master_seed": master_seed,
        "frozen_at": "2026-08-14",
        "seeds": seeds,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def gate1_seeds():
    cache = load_seeds(LOSS_SEEDS_CACHE)
    seeds = [int(rec["seed"]) for rec in cache if isinstance(rec, dict) and rec.get("seed")]
    return sorted(set(seeds))


def gate2_seeds():
    path = os.path.join(SEEDS_DIR, "historical_suite.json")
    if os.path.exists(path):
        return load_seeds(path)["seeds"]
    rng = random.Random(20260814)
    seeds = rng.sample(range(2_000_000_000, 4_000_000_000), 50)
    save_seeds(path, seeds, 20260814, "Gate 2 historical multi-archetype suite")
    return seeds


def gate3_seeds():
    path = os.path.join(SEEDS_DIR, "HOLDOUT_V1_N100.json")
    if os.path.exists(path):
        return load_seeds(path)["seeds"]
    rng = random.Random(20260815)
    seeds = rng.sample(range(4_000_000_000, 6_000_000_000), 100)
    save_seeds(path, seeds, 20260815, "Frozen single-shot holdout HOLDOUT_V1_N100")
    return seeds


def judge(holdout, verbose=True):
    m = {
        "wr_delta": round(2 * holdout["win_rate"] - 1, 4),
        "mcv_delta": holdout["delta_mean_mcv"],
        "std_ratio": round(holdout["cand_std_mcv"] / max(1e-9, holdout["base_std_mcv"]), 4),
        "tail_p05_delta": round(holdout["cand_p05_mcv"] - holdout["base_p05_mcv"], 1),
        "max_added_pass_turns": holdout["max_added_pass_turns"],
        "latency_mean_ms": holdout["latency_mean_ms"],
        "latency_max_ms": holdout["latency_max_ms"],
    }
    checks = {
        "delta_wr_ge_plus2.5pct": m["wr_delta"] >= 0.025,
        "delta_mcv_ge_plus2000": m["mcv_delta"] >= 2000.0,
        "std_ratio_le_1.10": m["std_ratio"] <= 1.10,
        "p05_tail_protected": m["tail_p05_delta"] >= 0.0,
        "added_pass_turns_le_3": m["max_added_pass_turns"] <= 3,
        "latency_le_20ms_mean_200ms_max": m["latency_mean_ms"] <= 20.0 and m["latency_max_ms"] <= 200.0,
    }
    failed = [k for k, v in checks.items() if not v]
    verdict = "APPROVED" if not failed else "FALSIFIED"
    if verbose:
        print("\n=== GATE 4: STATISTICAL JUDGE ===")
        for k, v in m.items():
            print(f"  {k:<28} {v}")
        for k, v in checks.items():
            print(f"  [{'PASS' if v else 'FAIL'}] {k}")
        print(f"  VERDICT: {verdict}  failed_reasons={failed}")
    return {"verdict": verdict, "failed_reasons": failed, "metrics": m, "checks": checks, "promotable": verdict == "APPROVED"}


def _record_failure(experiment_id, candidate_hash, baseline_hash, gate1, gate2, gate3, judge, why):
    """Fail-path ledger record: a falsified experiment MUST be recorded so the
    memory gate can block repeat attempts."""
    ledger = AuditLedger(os.path.join(_PROJECT_ROOT, "reports", "experiment_ledger.jsonl"))
    record = ledger.append_record(
        experiment_id=experiment_id,
        baseline_id=f"APEX-3.5-PROD:{baseline_hash[:16]}",
        candidate_meta={"candidate_file": CANDIDATE_FILE, "candidate_hash": candidate_hash},
        hypothesis_spec={
            "variable_family": "Pricing",
            "target_archetype": "SUPPLY_COLLAPSE",
            "mechanism_hypothesis": "Regime-gated exit overlay / trend-filtered suppression / deferred capital deployment (card).",
        },
        exact_replay_res={"status": (gate1 or {}).get("status", "SKIPPED"), "win_rate": (gate1 or {}).get("win_rate")},
        historical_res={"status": (gate2 or {}).get("status", "SKIPPED"), "win_rate": (gate2 or {}).get("win_rate")},
        holdout_res={"holdout_suite": "HOLDOUT_V1_N100", "win_rate": None},
        judge_verdict=judge,
        promoted=False,
        provenance={
            "baseline_hash": baseline_hash,
            "candidate_hash": candidate_hash,
            "harness": "match_runner.py seat-balanced double-run (seat-asymmetry controlled)",
            "why": why,
        },
        regime_tags=["SUPPLY_COLLAPSE", "STRAWBERRY", "MELON"],
        priority_score=3.16,
    )
    with open(os.path.join(EXP_DIR, "verdict.json"), "w", encoding="utf-8") as f:
        json.dump({
            "experiment_id": experiment_id,
            "candidate_hash": candidate_hash,
            "baseline_hash": baseline_hash,
            "verdict": judge["verdict"],
            "failed_reasons": judge["failed_reasons"],
            "why": why,
            "gate1": gate1,
            "gate2": gate2,
            "gate3": gate3,
        }, f, indent=2)
    print(f"\nLEDGER record appended: {experiment_id} -> {judge['verdict']}")
    print(f"VERDICT saved: {os.path.join(EXP_DIR, 'verdict.json')}")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(SEEDS_DIR, exist_ok=True)
    candidate_hash = sha256(CANDIDATE_FILE)
    baseline_hash = sha256(os.path.join(_PROJECT_ROOT, "submission.py"))
    print(f"{EXP_ID}  baseline_hash={baseline_hash[:16]}  candidate_hash={candidate_hash[:16]}")

    # ---- Gate 1: Exact Replay of 46 real loss seeds ----
    g1_seeds = gate1_seeds()
    print(f"\n=== GATE 1: EXACT REPLAY ({len(g1_seeds)} real loss seeds) ===")
    g1_res = load_seeds(os.path.join(RESULTS_DIR, "gate1.json"), required=False)
    if not g1_res:
        g1_res = run_paired(g1_seeds, max_workers=MAX_WORKERS, candidate_path=CANDIDATE_FILE, progress_file=os.path.join(RESULTS_DIR, "gate1.json"))
    s1 = summarize(g1_res)
    g1_ok = s1["win_rate"] >= 0.60 and s1["errors"] == 0
    print(f"  WR={s1['win_rate']:.3f} ({s1['wins']}/{s1['n']})  cand_delta_mcv={s1['delta_mean_mcv']:+,.0f}  errors={s1['errors']}")
    print(f"  GATE 1: {'PASS' if g1_ok else 'FAIL'}")
    if not g1_ok:
        _record_failure(
            EXP_ID, candidate_hash, baseline_hash,
            gate1={"status": "FAIL", "win_rate": s1["win_rate"], "n": s1["n"], "matches": s1["matches"]},
            gate2=None, gate3=None,
            judge={"verdict": "FALSIFIED", "failed_reasons": ["gate_1_exact_replay_below_60pct"], "metrics": {}, "checks": {}, "promotable": False},
            why=f"Gate 1 exact replay: WR {s1['win_rate']:.3f} < 0.60 on {len(g1_seeds)} real loss seeds.",
        )
        print("  STOPPING: exact replay did not clear 60% WR.")
        return

    # ---- Gate 2: Historical Suite (50 seeds, 10 groups x 5) ----
    g2_seeds = gate2_seeds()
    print(f"\n=== GATE 2: HISTORICAL SUITE ({len(g2_seeds)} seeds) ===")
    g2_res = load_seeds(os.path.join(RESULTS_DIR, "gate2.json"), required=False)
    if not g2_res:
        g2_res = run_paired(g2_seeds, max_workers=MAX_WORKERS, candidate_path=CANDIDATE_FILE, progress_file=os.path.join(RESULTS_DIR, "gate2.json"))
    s2 = summarize(g2_res)
    groups = []
    for i in range(0, len(g2_res), 5):
        chunk = g2_res[i:i + 5]
        wr = sum(r.get("win_points", 0.0) for r in chunk) / (2 * len(chunk))
        groups.append(round(wr, 3))
    g2_ok = s2["win_rate"] >= 0.75 and min(groups) >= 0.60 and s2["errors"] == 0
    print(f"  WR={s2['win_rate']:.3f} ({s2['wins']}/{s2['n']})  cand_delta_mcv={s2['delta_mean_mcv']:+,.0f}  group_WRs={groups}")
    print(f"  GATE 2: {'PASS' if g2_ok else 'FAIL'}")
    if not g2_ok:
        _record_failure(
            EXP_ID, candidate_hash, baseline_hash,
            gate1={"status": "PASS", "win_rate": s1["win_rate"], "n": s1["n"], "matches": s1["matches"]},
            gate2={"status": "FAIL", "win_rate": s2["win_rate"], "n": s2["n"], "matches": s2["matches"]},
            gate3=None,
            judge={"verdict": "FALSIFIED", "failed_reasons": ["gate_2_historical_suite_below_floors"], "metrics": {}, "checks": {}, "promotable": False},
            why=f"Gate 2 historical suite: WR {s2['win_rate']:.3f} < 0.75 or group floor violated ({groups}).",
        )
        print("  STOPPING: historical suite did not clear 75% / 60% group floors.")
        return

    # ---- Gate 3: Frozen Holdout, single shot ----
    g3_seeds = gate3_seeds()
    print(f"\n=== GATE 3: FROZEN HOLDOUT HOLDOUT_V1_N100 (single shot, {len(g3_seeds)} seeds) ===")
    g3_res = load_seeds(os.path.join(RESULTS_DIR, "gate3.json"), required=False)
    if not g3_res:
        g3_res = run_paired(g3_seeds, max_workers=MAX_WORKERS, candidate_path=CANDIDATE_FILE, progress_file=os.path.join(RESULTS_DIR, "gate3.json"))
    s3 = summarize(g3_res)
    print(f"  WR={s3['win_rate']:.3f} ({s3['wins']}/{s3['n']})  base_mcv={s3['base_mean_mcv']:,.0f} -> cand={s3['cand_mean_mcv']:,.0f} (delta {s3['delta_mean_mcv']:+,.0f})")
    print(f"  p05: base={s3['base_p05_mcv']:,.0f} cand={s3['cand_p05_mcv']:,.0f}  std_ratio={s3['cand_std_mcv'] / max(1e-9, s3['base_std_mcv']):.3f}")

    # ---- Gate 4: Statistical Judge ----
    verdict = judge(s3)

    # ---- Ledger + registry ----
    ledger = AuditLedger(os.path.join(_PROJECT_ROOT, "reports", "experiment_ledger.jsonl"))
    hypothesis_spec = {
        "variable_family": "Pricing",
        "target_archetype": "SUPPLY_COLLAPSE",
        "mechanism_hypothesis": "Regime-gated gentle-rebound exit: suppress SELL of collapsing decisive product (STRAWBERRY/MELON, 3-step drift <= -30%) until drift turns positive or price >= 24-step MA.",
    }
    record = ledger.append_record(
        experiment_id=EXP_ID,
        baseline_id=f"APEX-3.5-PROD:{baseline_hash[:16]}",
        candidate_meta={"candidate_file": CANDIDATE_FILE, "candidate_hash": candidate_hash},
        hypothesis_spec=hypothesis_spec,
        exact_replay_res={"status": "PASS" if g1_ok else "FAIL", "win_rate": s1["win_rate"], "n": s1["n"]},
        historical_res={"status": "PASS" if g2_ok else "FAIL", "win_rate": s2["win_rate"], "n": s2["n"]},
        holdout_res={"holdout_suite": "HOLDOUT_V1_N100", "win_rate": s3["win_rate"], "candidate_mean_mcv": s3["cand_mean_mcv"], "candidate_p05_mcv": s3["cand_p05_mcv"]},
        judge_verdict=verdict,
        promoted=False,
        parent_exp_id=None,
        provenance={
            "baseline_hash": baseline_hash,
            "candidate_hash": candidate_hash,
            "holdout_hash": sha256(os.path.join(SEEDS_DIR, "HOLDOUT_V1_N100.json")),
            "loss_seeds_cache": LOSS_SEEDS_CACHE,
        },
        regime_tags=["SUPPLY_COLLAPSE", "STRAWBERRY", "MELON"],
        priority_score=3.16,
        population_metrics={k: s3[k] for k in ("n", "win_rate", "base_mean_mcv", "cand_mean_mcv", "base_p05_mcv", "cand_p05_mcv", "base_std_mcv", "cand_std_mcv")},
    )
    print(f"\nLEDGER record appended: {EXP_ID} -> {verdict['verdict']}")

    registry = ChampionRegistry(os.path.join(_PROJECT_ROOT, "reports", "champion_registry.json"))
    if verdict["promotable"]:
        promo = registry.promote_challenger(
            challenger_meta={"candidate_file": CANDIDATE_FILE, "candidate_hash": candidate_hash, "baseline_hash": baseline_hash},
            judge_verdict=verdict,
            holdout_res={"holdout_suite": "HOLDOUT_V1_N100", "holdout_hash": sha256(os.path.join(SEEDS_DIR, "HOLDOUT_V1_N100.json")), "win_rate": s3["win_rate"], "candidate_mean_mcv": s3["cand_mean_mcv"], "candidate_p05_mcv": s3["cand_p05_mcv"]},
            version_tag=f"APEX-3.7-{EXP_ID}",
            release_confirmed=False,
        )
        print(f"REGISTRY: {promo['status']}  (deployment not confirmed -> remains baseline champion until Release Manager acts)")
    else:
        print("REGISTRY: unchanged (candidate falsified)")

    with open(os.path.join(EXP_DIR, "verdict.json"), "w", encoding="utf-8") as f:
        json.dump({
            "experiment_id": EXP_ID,
            "candidate_hash": candidate_hash,
            "baseline_hash": baseline_hash,
            "gate1": {"status": "PASS" if g1_ok else "FAIL", **s1},
            "gate2": {"status": "PASS" if g2_ok else "FAIL", **s2},
            "gate3": {"status": "COMPLETED", **s3},
            "gate4": verdict,
            "ledger_record": record.get("experiment_id"),
        }, f, indent=2)
    print(f"\nVERDICT saved: {os.path.join(EXP_DIR, 'verdict.json')}")


if __name__ == "__main__":
    main()