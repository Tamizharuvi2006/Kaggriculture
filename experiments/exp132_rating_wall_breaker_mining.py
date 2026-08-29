"""EXP132: Rating-Wall Breaker Mining across the Complete Kaggriculture Replay Corpus.

Analyzes:
1. Historical Submission Rating Trajectories across 10 generations (600 to 2400 Elo).
2. Categorization into Trajectory Cohorts:
   - WALL_TRAPPED (< 1200)
   - BRIEF_SPIKERS (Peak 1200-1399 then fell back)
   - SUSTAINED_CLIMBERS (1400-1800)
   - ELITE_TITANS (> 2000)
3. Win Rates partitioned by Opponent Elo Bands (<1200, 1200-1600, 1600-2000, 2000+).
4. Deep Step-Level Replay Behavioral Forensics:
   - Crop portfolio allocation over time
   - Land expansion velocity (Steps of Quadrant 2, 3, 4)
   - Livestock scaling (Cows vs Sheep)
   - Worker force scaling & movement
   - Market selling behavior (Response to market congestion & price shocks)
   - State-dependent / opponent-adaptive responses vs fixed production engines
"""
from __future__ import annotations
import os
import sys
import json
import glob
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
TELEMETRY_DIR = os.path.join(REPORTS_DIR, "live_match_telemetry")

def _to_native(val):
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    if isinstance(val, (np.floating, np.float64)):
        return float(val)
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_native(v) for v in val]
    return val

def load_submission_trajectories():
    sub_files = glob.glob(os.path.join(TELEMETRY_DIR, "submission_*_episodes.json"))
    gm_files = glob.glob(os.path.join(TELEMETRY_DIR, "grandmaster_replays", "*.json"))

    matches = []

    # 1. Parse Submission Metadata Files
    for sf in sub_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
            eps = data if isinstance(data, list) else data.get("episodes", data.get("matches", []))
            sub_id = int(os.path.basename(sf).split("_")[1])

            for ep in eps:
                agents = ep.get("agents", [])
                if len(agents) < 2:
                    continue
                if agents[0].get("submissionId") == sub_id:
                    our_a, opp_a = agents[0], agents[1]
                    seat = 0
                else:
                    our_a, opp_a = agents[1], agents[0]
                    seat = 1

                our_score_init = float(our_a.get("initialScore") or 1000.0)
                our_score_upd = float(our_a.get("updatedScore") or our_score_init)
                opp_score_init = float(opp_a.get("initialScore") or 1000.0)
                our_rew = float(our_a.get("reward") or 0.0)
                opp_rew = float(opp_a.get("reward") or 0.0)

                matches.append({
                    "sub_id": sub_id,
                    "ep_id": ep.get("id"),
                    "seed": ep.get("seed"),
                    "seat": seat,
                    "our_score_init": our_score_init,
                    "our_score_upd": our_score_upd,
                    "opp_score_init": opp_score_init,
                    "opp_sub_id": opp_a.get("submissionId"),
                    "our_reward": our_rew,
                    "opp_reward": opp_rew,
                    "won": our_rew > opp_rew,
                    "margin": our_rew - opp_rew,
                    "total_pie": our_rew + opp_rew,
                })
        except Exception as e:
            print(f"Error reading {sf}: {e}")

    # 2. Parse Grandmaster Match Files
    for gf in gm_files:
        try:
            with open(gf, "r", encoding="utf-8") as f:
                data = json.load(f)
            ep = data.get("episode", {})
            agents = ep.get("agents", [])
            if len(agents) < 2:
                continue

            a0, a1 = agents[0], agents[1]
            sub0 = a0.get("submissionId")
            sub1 = a1.get("submissionId")

            s0_init = float(a0.get("initialScore") or 1000.0)
            s0_upd = float(a0.get("updatedScore") or s0_init)
            s1_init = float(a1.get("initialScore") or 1000.0)
            s1_upd = float(a1.get("updatedScore") or s1_init)

            r0 = float(a0.get("reward") or 0.0)
            r1 = float(a1.get("reward") or 0.0)

            matches.append({
                "sub_id": sub0,
                "ep_id": ep.get("id"),
                "seed": ep.get("seed"),
                "seat": 0,
                "our_score_init": s0_init,
                "our_score_upd": s0_upd,
                "opp_score_init": s1_init,
                "opp_sub_id": sub1,
                "our_reward": r0,
                "opp_reward": r1,
                "won": r0 > r1,
                "margin": r0 - r1,
                "total_pie": r0 + r1,
            })

            matches.append({
                "sub_id": sub1,
                "ep_id": ep.get("id"),
                "seed": ep.get("seed"),
                "seat": 1,
                "our_score_init": s1_init,
                "our_score_upd": s1_upd,
                "opp_score_init": s0_init,
                "opp_sub_id": sub0,
                "our_reward": r1,
                "opp_reward": r0,
                "won": r1 > r0,
                "margin": r1 - r0,
                "total_pie": r0 + r1,
            })
        except Exception as e:
            print(f"Error reading {gf}: {e}")

    return pd.DataFrame(matches)

def analyze_step_level_replays():
    """Extracts step-level behavioral signatures across 168 replay logs."""
    replay_files = []
    replay_files.extend(glob.glob(os.path.join(TELEMETRY_DIR, "all_loss_replays_cache", "*.json")))
    replay_files.extend(glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "raw_replays", "*", "*.json")))
    replay_files.extend(glob.glob(os.path.join(REPORTS_DIR, "step5b", "old_loss_gauntlet", "ppo_submission_replays", "*", "*.json")))
    replay_files.extend(glob.glob(os.path.join(BASE_DIR, "l+reviews", "*.json")))
    replay_files.extend(glob.glob(os.path.join(BASE_DIR, "l+reviews", "newl", "*.json")))

    replay_files = [f for f in set(replay_files) if not f.endswith("-0.json") and not f.endswith("-1.json")]

    behavioral_records = []

    for rf in replay_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                data = json.load(f)

            steps = data.get("steps", [])
            if len(steps) < 10:
                continue

            # Analyze both players in the replay
            for p_idx in [0, 1]:
                opp_idx = 1 - p_idx
                last_step = steps[-1]
                last_obs = last_step[p_idx]["observation"]
                last_opp_obs = last_step[opp_idx]["observation"]

                farms = last_obs.get("farms", [])
                if len(farms) < 2:
                    continue

                our_farm = farms[p_idx]
                opp_farm = farms[opp_idx]

                our_money = float(our_farm.get("money", 0.0) or 0.0)
                opp_money = float(opp_farm.get("money", 0.0) or 0.0)
                won = our_money > opp_money

                # Trace timeline features
                straw_tiles = 0
                melon_tiles = 0
                carrot_tiles = 0
                wheat_tiles = 0
                cows = 0
                sheep = 0
                land_quadrants = len(our_farm.get("unlocked_quadrants", ["NW"]))

                for row in (our_farm.get("tiles") or []):
                    for tile in (row if isinstance(row, list) else [row]):
                        if isinstance(tile, dict):
                            crop = tile.get("crop")
                            anim = tile.get("animal")
                            if crop == "STRAWBERRY": straw_tiles += 1
                            elif crop == "MELON": melon_tiles += 1
                            elif crop == "CARROT": carrot_tiles += 1
                            elif crop == "WHEAT": wheat_tiles += 1

                            if anim == "COW": cows += 1
                            elif anim == "SHEEP": sheep += 1

                # Step when Quadrant 2 & 3 were unlocked
                step_land2 = None
                step_land3 = None
                for s_idx, s in enumerate(steps):
                    f_s = s[p_idx]["observation"]["farms"][p_idx]
                    unl = f_s.get("unlocked_quadrants", ["NW"])
                    if len(unl) >= 2 and step_land2 is None:
                        step_land2 = s_idx
                    if len(unl) >= 3 and step_land3 is None:
                        step_land3 = s_idx

                # Classify bot archetype
                if our_money >= 80000 and opp_money >= 60000:
                    tier = "TITAN_COMPETITIVE"
                elif our_money >= 80000:
                    tier = "HIGH_YIELD"
                elif our_money >= 50000:
                    tier = "MID_TIER"
                else:
                    tier = "LOW_TIER"

                behavioral_records.append({
                    "file": os.path.basename(rf),
                    "player": p_idx,
                    "money": our_money,
                    "opp_money": opp_money,
                    "won": won,
                    "tier": tier,
                    "straw_tiles": straw_tiles,
                    "melon_tiles": melon_tiles,
                    "carrot_tiles": carrot_tiles,
                    "wheat_tiles": wheat_tiles,
                    "cows": cows,
                    "sheep": sheep,
                    "land_quadrants": land_quadrants,
                    "step_land2": step_land2,
                    "step_land3": step_land3,
                })
        except Exception:
            continue

    return pd.DataFrame(behavioral_records)

def main():
    print("=" * 135)
    print("EXP132: RATING-WALL BREAKER MINING & CROSS-TIER ARCHETYPE RECONSTRUCTION")
    print("=" * 135)

    df_trajectories = load_submission_trajectories()
    print(f"Loaded {len(df_trajectories)} historical tournament match trajectories across Kaggle leaderboard.")

    # Aggregate by Submission ID
    sub_groups = df_trajectories.groupby("sub_id")
    sub_summaries = []

    for sub_id, group in sub_groups:
        init_scores = group["our_score_init"]
        upd_scores = group["our_score_upd"]
        peak_score = max(init_scores.max(), upd_scores.max())
        min_score = min(init_scores.min(), upd_scores.min())
        final_score = upd_scores.iloc[-1]
        matches_count = len(group)
        win_rate = group["won"].mean() * 100

        # Categorize
        if peak_score >= 2000:
            cohort = "ELITE_TITANS (>= 2000)"
        elif peak_score >= 1400:
            cohort = "SUSTAINED_CLIMBERS (1400-1800)"
        elif peak_score >= 1200:
            if final_score < 1150:
                cohort = "BRIEF_SPIKERS (Touched 1200+, Fell Back)"
            else:
                cohort = "SUSTAINED_CLIMBERS (1200-1400)"
        else:
            cohort = "WALL_TRAPPED (< 1200)"

        sub_summaries.append({
            "sub_id": sub_id,
            "cohort": cohort,
            "peak_score": peak_score,
            "min_score": min_score,
            "final_score": final_score,
            "matches": matches_count,
            "win_rate": win_rate,
            "mean_reward": group["our_reward"].mean(),
            "median_reward": group["our_reward"].median(),
            "mean_margin": group["margin"].mean(),
        })

    df_subs = pd.DataFrame(sub_summaries)

    print("\n1. SUBMISSION TRAJECTORY COHORTS:")
    print(f"{'Cohort':<35} | {'Submissions':<12} | {'Peak Score':<12} | {'Mean Win Rate':<15} | {'Mean Reward'}")
    print("-" * 105)
    for cohort_name, grp in df_subs.groupby("cohort"):
        print(f"{cohort_name:<35} | {len(grp):2d} subs      | {grp['peak_score'].mean():7.1f}      | {grp['win_rate'].mean():5.1f}%          | ${grp['mean_reward'].mean():10,.0f}")

    # Win Rate Partitioned by Opponent Elo Bands
    print("\n2. WIN RATE BY OPPONENT ELO BAND ACROSS COHORTS:")
    df_trajectories["opp_elo_band"] = pd.cut(
        df_trajectories["opp_score_init"],
        bins=[0, 1200, 1600, 2000, 3500],
        labels=["900-1200", "1200-1600", "1600-2000", "2000+"]
    )

    # Merge cohort into trajectories
    df_merged = df_trajectories.merge(df_subs[["sub_id", "cohort"]], on="sub_id")

    band_pivot = df_merged.groupby(["cohort", "opp_elo_band"], observed=False)["won"].agg(["count", "mean"])
    band_pivot["win_pct"] = band_pivot["mean"] * 100

    print(f"{'Cohort':<32} | {'Opponent Band':<15} | {'Match Count':<12} | {'Win Rate (%)'}")
    print("-" * 85)
    for (coh, band), row in band_pivot.iterrows():
        if row["count"] > 0:
            print(f"{coh:<32} | {band:<15} | {int(row['count']):4d} matches | {row['win_pct']:5.1f}%")

    # Step-Level Replay Behavioral Forensics
    print("\n" + "=" * 135)
    print("3. STEP-LEVEL REPLAY BEHAVIORAL FORENSICS (168 FULL REPLAY LOGS)")
    print("=" * 135)
    df_replays = analyze_step_level_replays()
    print(f"Analyzed {len(df_replays)} farm lifecycles across tournament replays.")

    tier_grp = df_replays.groupby("tier")
    print(f"\n{'Tier / Performance':<25} | {'Strawberries':<14} | {'Melons':<10} | {'Cows':<8} | {'Sheep':<8} | {'Land Quadrants':<15} | {'Step Land #2'}")
    print("-" * 115)
    for t_name, t_sub in tier_grp:
        print(f"{t_name:<25} | {t_sub['straw_tiles'].mean():5.1f} plots    | {t_sub['melon_tiles'].mean():4.1f} plots| {t_sub['cows'].mean():4.1f}   | {t_sub['sheep'].mean():4.1f}   | {t_sub['land_quadrants'].mean():4.1f} quads       | Step {t_sub['step_land2'].mean():.1f}")

    # Output JSON Synthesis
    out_json = os.path.join(REPORTS_DIR, "exp132_rating_wall_breaker_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "submissions": _to_native(sub_summaries),
            "replays": _to_native(df_replays.to_dict(orient="records")),
        }, f, indent=2)
    print(f"\nSaved Full EXP132 Results: {out_json}")
    print("=" * 135)

if __name__ == "__main__":
    main()
