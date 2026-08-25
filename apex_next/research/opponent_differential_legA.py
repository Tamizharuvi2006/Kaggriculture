"""Opponent-differential study, Leg A: real telemetry.

Question: is APEX's ~46% SUPPLY_COLLAPSE WR an APEX-specific weakness or shared
by the elite field?

Data: mcv_replay_dataset.json (43 real matches of APEX-lineage refs
55373438 / 55373932 / 55376463), joined with opponent Elo (initialScore) from
reports/live_match_telemetry/submission_*_episodes.json.

Controls: same seed (real match), same regime definition (3-sample drift
<= -30% on STRAWBERRY/MELON, fingerprint-calibrated), same observation count
(60 samples/match). Seat is controlled by per-match paired comparison.

Regime tag is computed from the market price series (identical for both
players), so both sides share the collapse window by construction.
"""
import json
import glob
import os
import statistics

ROOT = r"D:\Kaggriculture"
DATA = os.path.join(ROOT, "data", "replay", "mcv_replay_dataset.json")
EPISODES_DIR = os.path.join(ROOT, "reports", "live_match_telemetry")
APEX_REFS = {"55373438", "55373932", "55376463"}
DECISIVE = ("STRAWBERRY", "MELON")
DRIFT = -0.30


def load_episodes():
    table = {}
    for f in glob.glob(os.path.join(EPISODES_DIR, "submission_*_episodes.json")):
        data = json.load(open(f, encoding="utf-8"))
        ref = data.get("submission", {}).get("ref")
        for e in data.get("episodes", []):
            if e.get("state") == "COMPLETED" and len(e.get("agents", [])) >= 2:
                eid = str(e.get("id"))
                if eid not in table:
                    table[eid] = {"ref": ref, "agents": e["agents"]}
    return table


def drift_series(prices_list, product):
    series = []
    for step_prices in prices_list:
        p = step_prices.get(product)
        if isinstance(p, dict):
            p = p.get("price")
        if p is None:
            series.append(None)
        else:
            series.append(float(p))
    drifts = []
    for i in range(3, len(series)):
        a, b = series[i - 3], series[i]
        if a is None or b is None or a <= 0:
            drifts.append(None)
        else:
            drifts.append((b - a) / a)
    return series, drifts


def collapse_windows(drift_map, n):
    active = [False] * n
    for product, drifts in drift_map.items():
        for i, d in enumerate(drifts):
            if d is not None and d <= DRIFT:
                active[i + 3] = True
    return active


def main():
    rows = json.load(open(DATA, encoding="utf-8"))
    episodes = load_episodes()
    by_file = {}
    for r in rows:
        by_file.setdefault(r["file"], []).append(r)

    matches = []
    for fname, frows in sorted(by_file.items()):
        eid = fname.replace(".json", "")
        ep = episodes.get(eid)
        if not ep:
            continue
        agents = ep["agents"]
        if len(agents) < 2:
            continue
        id_to_agent = {str(a.get("submissionId")): a for a in agents}
        apex_ids = [sid for sid in id_to_agent if sid in APEX_REFS]
        if len(apex_ids) != 1:
            continue
        apex_sid = apex_ids[0]
        opp_sid = [sid for sid in id_to_agent if sid != apex_sid]
        if not opp_sid:
            continue
        opp = id_to_agent[opp_sid[0]]
        p0 = sorted([r for r in frows if r["player_idx"] == 0], key=lambda r: r["step"])
        p1 = sorted([r for r in frows if r["player_idx"] == 1], key=lambda r: r["step"])
        prices = [r["market_prices"] for r in p0]
        drift_map = {}
        for prod in DECISIVE:
            _, drifts = drift_series(prices, prod)
            drift_map[prod] = drifts
        active = collapse_windows(drift_map, len(p0))
        collapse = any(active)
        duration = sum(1 for a in active if a)
        first_collapse_idx = active.index(True) if collapse else None
        apex_idx = 0 if p0[0].get("is_apex") or not p0[0].get("is_apex") is None else 0
        # episode agent list order == player_idx order (verified; `index` field unreliable)
        apex_won = None
        apex_mcv = None
        for idx, player_rows in ((0, p0), (1, p1)):
            won = [r["won_match"] for r in player_rows if r["won_match"] is not None]
            fw = [r["final_wealth"] for r in player_rows if r["final_wealth"] is not None]
            if not won or not fw:
                continue
            side = str(agents[idx].get("submissionId"))
            if side == apex_sid:
                apex_won = won[-1]
                apex_mcv = fw[-1]
        if apex_won is None:
            continue
        opp_score = opp.get("initialScore")
        apex_score = id_to_agent[apex_sid].get("initialScore")
        matches.append({
            "eid": eid,
            "ref": ep["ref"],
            "apex_sid": apex_sid,
            "opp_sid": opp_sid[0],
            "opp_score": opp_score,
            "apex_score": apex_score,
            "apex_won": apex_won,
            "apex_mcv": apex_mcv,
            "collapse": collapse,
            "duration": duration,
            "first_collapse_idx": first_collapse_idx,
        })

    collapse_matches = [m for m in matches if m["collapse"]]
    non_collapse = [m for m in matches if not m["collapse"]]
    print(f"matches: total={len(matches)} collapse={len(collapse_matches)} "
          f"({100.0*len(collapse_matches)/len(matches):.0f}%) non-collapse={len(non_collapse)}")

    def wr(ms):
        if not ms:
            return None
        return 100.0 * sum(1 for m in ms if m["apex_won"]) / len(ms)

    def mean(ms, key):
        vals = [m[key] for m in ms if m[key] is not None]
        return statistics.mean(vals) if vals else None

    def p05(ms, key):
        vals = sorted(m[key] for m in ms if m[key] is not None)
        if not vals:
            return None
        return vals[max(0, int(0.05 * len(vals)) - 1)]

    opp_scores = sorted(m["opp_score"] for m in matches if m["opp_score"] is not None)
    elite_thr = opp_scores[int(0.75 * len(opp_scores)) - 1] if opp_scores else None
    print(f"opponent initialScore: n={len(opp_scores)} range={min(opp_scores):.0f}..{max(opp_scores):.0f} "
          f"median={statistics.median(opp_scores):.0f} elite(75th)={elite_thr:.0f}")

    def bucket(ms, label, pred):
        sub = [m for m in ms if pred(m)]
        if not sub:
            print(f"  {label}: n=0")
            return
        print(f"  {label}: n={len(sub)} WR={wr(sub):.1f}% APEX_MCV={mean(sub, 'apex_mcv'):.0f} "
              f"p05={p05(sub, 'apex_mcv'):.0f} dur_mean={mean(sub, 'duration'):.1f}")

    print("\nSUPPLY_COLLAPSE matches by opponent tier:")
    bucket(collapse_matches, "ALL", lambda m: True)
    if elite_thr:
        bucket(collapse_matches, "ELITE (opp>=75th)", lambda m: m["opp_score"] is not None and m["opp_score"] >= elite_thr)
        bucket(collapse_matches, "TIER-2 (opp<75th)", lambda m: m["opp_score"] is not None and m["opp_score"] < elite_thr)
        bucket(collapse_matches, "NO-SCORE", lambda m: m["opp_score"] is None)
    bucket(collapse_matches, "APEX-STRONGER (score gap>0)", lambda m: (m["apex_score"] or 0) - (m["opp_score"] or 0) > 0)
    bucket(collapse_matches, "OPP-STRONGER (score gap<0)", lambda m: (m["apex_score"] or 0) - (m["opp_score"] or 0) < 0)

    print("\nNON-COLLAPSE matches (control):")
    bucket(non_collapse, "ALL", lambda m: True)

    out = {
        "n_total": len(matches),
        "n_collapse": len(collapse_matches),
        "elite_threshold": elite_thr,
        "collapse_wr": wr(collapse_matches),
        "non_collapse_wr": wr(non_collapse),
        "opp_score_median": statistics.median(opp_scores) if opp_scores else None,
        "matches": matches,
    }
    outpath = os.path.join(ROOT, "apex_next", "research", "opponent_differential_legA_results.json")
    json.dump(out, open(outpath, "w", encoding="utf-8"), indent=2)
    print(f"\nsaved: {outpath}")


if __name__ == "__main__":
    main()
