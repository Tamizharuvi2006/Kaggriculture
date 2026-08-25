"""Regression verification: APEX 3.5 (apex35) vs APEX 3.6 PROD (submission.py).

Protocol (identical to the Gate-1 holdout):
  - seeds: the 46 real loss seeds (apex33_loss_seeds_cache.json)
  - 2 matches per seed (both seat orders) -> seat-balanced
  - byte-identical determinism rerun on 3 seeds
  - head-to-head 3.5 vs 3.6 + full 4-agent re-baseline on the same seeds

Status framing: "REGRESSION SUSPECTED" until this verification confirms it.
"""
import itertools
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from match_runner import run_single_match, run_paired  # noqa: E402

ROOT = r"D:\Kaggriculture"
OUT = os.path.join(ROOT, "apex_next", "research", "regression_verify_35_vs_36_results")
SEEDS_FILE = os.path.join(ROOT, "reports", "live_match_telemetry", "apex33_loss_seeds_cache.json")

AGENTS = {
    "apex35": os.path.join(ROOT, "generalization_pipeline", "submission_candidate_apex35.py"),
    "PROD36": os.path.join(ROOT, "submission.py"),
    "v18": os.path.join(ROOT, "baseline", "kaitofukami-v18.py"),
    "v83": os.path.join(ROOT, "baseline", "submission_v83_standalone.py"),
}


def load_seeds():
    cache = json.load(open(SEEDS_FILE, encoding="utf-8"))
    seeds = []
    for entry in cache:
        if isinstance(entry, dict):
            seeds.append(int(entry["seed"]))
        else:
            seeds.append(int(entry))
    return sorted(set(seeds))


def wilcoxon_paired(deltas):
    ranks = sorted((abs(d), 1 if d > 0 else -1) for d in deltas if d != 0)
    if not ranks:
        return 1.0, 0
    n = len(ranks)
    pos = sum(i + 1 for i, (_, sgn) in enumerate(ranks) if sgn > 0)
    W = min(pos, n * (n + 1) / 2 - pos)
    # normal approximation with continuity correction
    mu = n * (n + 1) / 4
    sigma = (n * (n + 1) * (2 * n + 1) / 24) ** 0.5
    z = (W - mu + 0.5) / sigma
    from math import erf, sqrt
    p = 1 - 0.5 * (1 + erf(z / sqrt(2)))
    return min(max(p, 0.0), 1.0), n


def binomial_two_sided(wins, n):
    from math import comb
    if n == 0:
        return 1.0
    p = 0.5
    total = sum(comb(n, k) for k in range(0, n + 1))
    lo = sum(comb(n, k) for k in range(0, min(wins, n - wins) + 1))
    return min(1.0, 2.0 * lo / total)


def seat_detail(results, cand_label, base_label):
    rows = []
    for r in results:
        m0b, m1b = r["base_mcvs"] if isinstance(r.get("base_mcvs"), list) else [r["base_mcv"]] * 2
        m0c, m1c = r["cand_mcvs"] if isinstance(r.get("cand_mcvs"), list) else [r["cand_mcv"]] * 2
        rows.append({
            "seed": r["seed"],
            "seat0_win_cand": m0c > m0b,
            "seat1_win_cand": m1c > m1b,
            "base_mcv": r["base_mcv"],
            "cand_mcv": r["cand_mcv"],
            "base_pass": r.get("base_pass_turns", 0) + r.get("cand_pass_turns", 0) // 2,
            "error": r.get("error"),
        })
    return rows


def summarize_head_to_head(results):
    errs = [r for r in results if r.get("error")]
    rows = seat_detail(results, "cand", "base")
    deltas = [r["cand_mcv"] - r["base_mcv"] for r in rows]
    seed_wins = sum(1 for r in rows if r["cand_mcv"] > r["base_mcv"])
    seed_losses = sum(1 for r in rows if r["cand_mcv"] < r["base_mcv"])
    seed_splits = sum(1 for r in rows if r["cand_mcv"] == r["base_mcv"])
    seat0 = sum(1 for r in rows if r["seat0_win_cand"])
    seat1 = sum(1 for r in rows if r["seat1_win_cand"])
    cand_mcvs = [r["cand_mcv"] for r in rows]
    base_mcvs = [r["base_mcv"] for r in rows]
    p05 = sorted(cand_mcvs)[max(0, int(0.05 * len(cand_mcvs)) - 1)]
    p05b = sorted(base_mcvs)[max(0, int(0.05 * len(base_mcvs)) - 1)]
    w_p, w_n = wilcoxon_paired(deltas)
    b_p = binomial_two_sided(seed_wins, seed_wins + seed_losses)
    return {
        "n_seeds": len(rows),
        "seed_wins": seed_wins,
        "seed_losses": seed_losses,
        "seed_splits": seed_splits,
        "win_points_total": seed_wins * 2 + seed_splits,
        "win_points_max": len(rows) * 2,
        "seat0_wins_cand": seat0,
        "seat1_wins_cand": seat1,
        "cand_mean_mcv": statistics.mean(cand_mcvs),
        "base_mean_mcv": statistics.mean(base_mcvs),
        "cand_median_mcv": statistics.median(cand_mcvs),
        "base_median_mcv": statistics.median(base_mcvs),
        "cand_p05_mcv": p05,
        "base_p05_mcv": p05b,
        "cand_std_mcv": statistics.stdev(cand_mcvs) if len(cand_mcvs) > 1 else 0,
        "base_std_mcv": statistics.stdev(base_mcvs) if len(base_mcvs) > 1 else 0,
        "wilcoxon_p": round(w_p, 4),
        "binomial_p": round(b_p, 4),
        "errors": len(errs),
        "max_abs_delta": max(abs(d) for d in deltas),
    }


def determinism_check(seeds, a_path, b_path, label):
    results = {}
    for seed in seeds:
        for swap in (False, True):
            r = run_single_match(seed, swap=swap, candidate_path=a_path, baseline_path=b_path)
            results[(seed, swap)] = (r["base_mcv"], r["cand_mcv"])
    results2 = {}
    for seed in seeds:
        for swap in (False, True):
            r = run_single_match(seed, swap=swap, candidate_path=a_path, baseline_path=b_path)
            results2[(seed, swap)] = (r["base_mcv"], r["cand_mcv"])
    identical = results == results2
    print(f"determinism {label}: {'IDENTICAL (byte-level)' if identical else 'MISMATCH!'}")
    return identical


def main():
    os.makedirs(OUT, exist_ok=True)
    seeds = load_seeds()
    print(f"seeds: {len(seeds)} (apex33 loss cache)")
    report = {"seeds": seeds, "seed_count": len(seeds), "protocol": "2 matches/seed, seats swapped, seat-balanced"}

    # 1) head-to-head: apex35 (candidate) vs PROD36 (baseline) on all 46 seeds
    print("\n=== HEAD-TO-HEAD: apex35 vs PROD36 (46 seeds, seat-balanced) ===")
    h2h = run_paired(
        seeds, max_workers=4, seat_balanced=True,
        candidate_path=AGENTS["apex35"], baseline_path=AGENTS["PROD36"],
        progress_file=os.path.join(OUT, "h2h_apex35_vs_prod36.json"),
    )
    s = summarize_head_to_head(h2h)
    report["head_to_head_apex35_vs_PROD36"] = s
    print(json.dumps(s, indent=2))

    # 2) determinism rerun on 3 seeds
    det_seeds = seeds[:3]
    ok = determinism_check(det_seeds, AGENTS["apex35"], AGENTS["PROD36"], "apex35 vs PROD36")
    report["determinism_identical"] = ok

    # 3) full re-baseline round-robin on the same 46 seeds
    print("\n=== RE-BASELINE: 4 agents x 46 seeds (same protocol) ===")
    pair_records = []
    for a, b in itertools.combinations(sorted(AGENTS), 2):
        key = f"{a}__vs__{b}"
        results = run_paired(
            seeds, max_workers=4, seat_balanced=True,
            candidate_path=AGENTS[a], baseline_path=AGENTS[b],
            progress_file=os.path.join(OUT, f"rebaseline_{key}.json"),
        )
        for r in results:
            pair_records.append({
                "pair": key, "seed": r["seed"],
                "mcv_a": r["base_mcv"], "mcv_b": r["cand_mcv"],
                "wp": r["win_points"], "err": r.get("error"),
            })
        print(f"{key}: done", flush=True)

    per_agent = {n: {} for n in AGENTS}
    for rec in pair_records:
        a, b = rec["pair"].split("__vs__")
        for side, key in ((a, "mcv_a"), (b, "mcv_b")):
            bucket = per_agent[side]
            opp = b if side == a else a
            bucket.setdefault(opp, []).append(rec[key])
            bucket.setdefault("_all", []).append(rec[key])
        # win accounting: rec['wp'] belongs to candidate = a
        per_agent[a].setdefault("_wins", []).append(rec["wp"] / 2.0)
        per_agent[b].setdefault("_wins", []).append(1.0 - rec["wp"] / 2.0)

    rebaseline = {}
    print(f"\n{'agent':<8} {'vs':<8} {'n':>3} {'WR%':>6} {'mean':>8} {'median':>8} {'p05':>8} {'std':>8}")
    for name in sorted(AGENTS):
        wins = per_agent[name]["_wins"]
        all_m = per_agent[name]["_all"]
        p05 = sorted(all_m)[max(0, int(0.05 * len(all_m)) - 1)]
        rebaseline[name] = {
            "wr_pct": round(100.0 * sum(wins) / len(wins), 1),
            "mean_mcv": round(statistics.mean(all_m), 0),
            "median_mcv": round(statistics.median(all_m), 0),
            "p05_mcv": round(p05, 0),
            "std_mcv": round(statistics.stdev(all_m), 0) if len(all_m) > 1 else 0,
            "n_matches": len(all_m),
        }
        print(f"{name:<8} {'ALL':<8} {len(all_m):>3} {rebaseline[name]['wr_pct']:>6.1f} "
              f"{rebaseline[name]['mean_mcv']:>8.0f} {rebaseline[name]['median_mcv']:>8.0f} "
              f"{rebaseline[name]['p05_mcv']:>8.0f} {rebaseline[name]['std_mcv']:>8.0f}")
    for name in sorted(AGENTS):
        for opp in sorted(AGENTS):
            if opp == name:
                continue
            vals = per_agent[name].get(opp) or []
            if not vals:
                continue
            w_opp = [w for w, (side, o) in _zip_wins(per_agent, pair_records, name, opp)]
            # simpler: compute WR vs opp from pair records
            opp_wins = _opp_wins(pair_records, name, opp)
            print(f"{name:<8} vs {opp:<8} n={len(vals):>3} WR={opp_wins:.1f}%")
            rebaseline[name].setdefault("by_opponent", {})[opp] = round(opp_wins, 1)
    report["rebaseline"] = rebaseline

    with open(os.path.join(OUT, "regression_verification_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nsaved: {OUT}/regression_verification_report.json")


def _zip_wins(per_agent, pair_records, name, opp):
    out = []
    for rec in pair_records:
        a, b = rec["pair"].split("__vs__")
        if {a, b} != {name, opp}:
            continue
        share = rec["wp"] / 2.0 if rec["pair"].startswith(name) else 1.0 - rec["wp"] / 2.0
        out.append((share, opp))
    return out


def _opp_wins(pair_records, name, opp):
    vals = _zip_wins(None, pair_records, name, opp)
    return 100.0 * sum(v for v, _ in vals) / len(vals) if vals else 0.0


if __name__ == "__main__":
    main()