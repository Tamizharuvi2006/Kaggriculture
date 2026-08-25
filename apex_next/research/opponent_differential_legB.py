"""Opponent-differential study, Leg B: controlled local round-robin.

Question: does APEX's SUPPLY_COLLAPSE WR drop relative to the reference
frontier when all agents face the SAME opponents, seeds, seats and regime
definition?

Design: round-robin of 4 local agents on 30 fresh deterministic seeds.
  agents = APEX PROD (submission.py), v18 (kaitofukami-v18), v83 standalone,
           apex35 (generalization candidate)
Each pair runs the seat-balanced double-run (2 matches/seed, seats swapped)
via match_runner.run_paired. Regime tag is computed from the shared market
price series (identical for both players within a match), so both sides of a
match share the collapse tag by construction.

Per agent: WR / mean MCV / p05 in collapse-tagged vs non-collapse matches,
against the same 3 opponents on the same 30 seeds -> the regime-attributable
gap is controlled for opponent mix.
"""
import itertools
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from match_runner import run_paired  # noqa: E402

ROOT = r"D:\Kaggriculture"
OUT_DIR = os.path.join(ROOT, "apex_next", "research", "opponent_differential_legB_results")
MASTER = 20260814
N_SEEDS = 30

AGENTS = {
    "APEX": os.path.join(ROOT, "submission.py"),
    "v18": os.path.join(ROOT, "baseline", "kaitofukami-v18.py"),
    "v83": os.path.join(ROOT, "baseline", "submission_v83_standalone.py"),
    "apex35": os.path.join(ROOT, "generalization_pipeline", "submission_candidate_apex35.py"),
}


def seed_set(n):
    return [(MASTER * 1_000_003 + i * 7919) % (2 ** 31) for i in range(n)]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    seeds = seed_set(N_SEEDS)
    records = []
    for a, b in itertools.combinations(sorted(AGENTS), 2):
        key = f"{a}__vs__{b}"
        progress = os.path.join(OUT_DIR, f"{key}.json")
        results = run_paired(
            seeds,
            max_workers=4,
            seat_balanced=True,
            progress_file=progress,
            candidate_path=AGENTS[a],
            baseline_path=AGENTS[b],
        )
        for r in results:
            records.append({
                "opp_a": a,
                "opp_b": b,
                "cand_side": a,
                "seed": r["seed"],
                "collapse": bool(r.get("regime_tags")),
                "min_drift3": min((t.get("min_drift3") for t in (r.get("regime_tags") or []) if t.get("min_drift3") is not None), default=None),
                "win_points": r.get("win_points", 0.0),
                "mcv_a": r.get("base_mcv", 0.0),
                "mcv_b": r.get("cand_mcv", 0.0),
            })
        print(f"{key}: done ({len(results)} seeds)", flush=True)

    # per-agent stats: collapse-tagged matches (full-match tag is near-universal),
    # partitioned by collapse severity (min_drift3 of the decisive products,
    # identical for both sides since prices are market-wide).
    rows = {name: {} for name in AGENTS}
    for rec in records:
        sev = rec.get("min_drift3")
        bucket = "severe" if (sev is not None and sev <= -0.60) else (
            "mild" if sev is not None else "none")
        a_share = rec["win_points"] / 2.0
        b_share = 1.0 - a_share
        rows[rec["opp_a"]].setdefault(bucket, []).append({"win": a_share, "mcv": rec["mcv_a"]})
        rows[rec["opp_b"]].setdefault(bucket, []).append({"win": b_share, "mcv": rec["mcv_b"]})

    summary = {}
    print(f"\n{'agent':<8} {'set':<8} {'n':>3} {'WR%':>6} {'MCV':>8} {'p05':>8} {'gapWR':>6}")
    for name in sorted(AGENTS):
        for bucket in ("severe", "mild", "none"):
            entries = rows[name].get(bucket) or []
            if not entries:
                continue
            wins = sum(e["win"] for e in entries)
            mcvs = [e["mcv"] for e in entries]
            w = 100.0 * wins / len(entries)
            p05 = sorted(mcvs)[max(0, int(0.05 * len(mcvs)) - 1)]
            summary.setdefault(name, {})[bucket] = {
                "n": len(entries), "wr_pct": round(w, 1),
                "mcv_mean": round(statistics.mean(mcvs), 0), "p05": round(p05, 0),
            }
            print(f"{name:<8} {bucket:<8} {len(entries):>3} {w:>6.1f} "
                  f"{statistics.mean(mcvs):>8.0f} {p05:>8.0f}")

    refs = [summary[n]["severe"]["wr_pct"] for n in summary if n != "APEX" and "severe" in summary[n]]
    apex_c = summary.get("APEX", {}).get("severe", {}).get("wr_pct")
    ref_med = statistics.median(refs) if refs else None
    apex_mcv = summary.get("APEX", {}).get("severe", {}).get("mcv_mean")
    ref_mcv = statistics.median(
        [summary[n]["severe"]["mcv_mean"] for n in summary if n != "APEX" and "severe" in summary[n]]
    ) if refs else None
    result = {
        "design": "round-robin 4 agents x 30 seeds, seat-balanced double-run, shared regime tag; "
                  "full-match collapse tag is near-universal -> partitioned by severity (min_drift3 <= -0.60 severe)",
        "seeds": seeds,
        "agents": {k: v for k, v in AGENTS.items()},
        "per_agent": summary,
        "apex_severe_wr_pct": apex_c,
        "reference_severe_wr_median_pct": ref_med,
        "apex_minus_reference_wr_pp": round(apex_c - ref_med, 1) if (apex_c is not None and ref_med is not None) else None,
        "apex_severe_mcv": apex_mcv,
        "reference_severe_mcv_median": ref_mcv,
        "apex_minus_reference_mcv": round(apex_mcv - ref_mcv, 1) if (apex_mcv is not None and ref_mcv is not None) else None,
    }
    out = os.path.join(OUT_DIR, "legB_summary.json")
    json.dump(result, open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()