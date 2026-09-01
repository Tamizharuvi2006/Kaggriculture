#!/usr/bin/env python3
"""Hard-Loss Failure Dataset & Temporal Divergence Miner for Kaggriculture.

Mines live loss replays across all historical submissions, reconstructs
turn-by-turn trajectory states, locates the exact step and phase of first
decisive divergence, clusters failure modes, and synthesizes structured
hard-negative pairs:
  State -> Opponent Pattern -> Our Failure Decision -> Prescribed Counter-Response
"""

from __future__ import annotations

import os
import sys
import json
import glob
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

OUTPUT_DATASET_PATH = Path(r"D:\kaggriculture\reports\live_match_telemetry\hard_loss_dataset.json")
TELEMETRY_DIR = Path(r"D:\kaggriculture\reports\live_match_telemetry")

def extract_divergence_from_replay(replay_data: Dict[str, Any], hero_sid: Optional[int] = None) -> Optional[Dict[str, Any]]:
    info = replay_data.get("info", {})
    eid = info.get("EpisodeId") or replay_data.get("id")
    seed = info.get("seed")
    agents = info.get("Agents") or replay_data.get("agents") or []
    rewards = replay_data.get("rewards") or [a.get("reward") for a in agents]
    
    if len(agents) < 2 or len(rewards) < 2:
        return None
        
    # Find hero
    hero_idx = None
    if hero_sid:
        for i, a in enumerate(agents):
            if a.get("submissionId") == hero_sid:
                hero_idx = i
                break
    if hero_idx is None:
        # Check by team name
        for i, a in enumerate(agents):
            name = a.get("Name", "") or a.get("name", "")
            if "tamizh" in name.lower():
                hero_idx = i
                break
    if hero_idx is None:
        hero_idx = 0 # Fallback
        
    opp_idx = 1 - hero_idx
    h_rew = rewards[hero_idx] or 0
    o_rew = rewards[opp_idx] or 0
    
    # Only process losses
    if h_rew >= o_rew:
        return None
        
    margin = h_rew - o_rew
    steps = replay_data.get("steps") or []
    if len(steps) < 10:
        return None
        
    h_name = agents[hero_idx].get("Name") or agents[hero_idx].get("name") or "Hero"
    o_name = agents[opp_idx].get("Name") or agents[opp_idx].get("name") or "Opponent"
    o_elo = agents[opp_idx].get("initialScore") or agents[opp_idx].get("updatedScore") or 600.0

    # Step-by-step wealth and asset tracing
    deltas = []
    h_cash = []
    o_cash = []
    h_quads_list = []
    o_quads_list = []
    h_anim_list = []
    o_anim_list = []
    h_work_list = []
    o_work_list = []
    
    for s_idx, frame in enumerate(steps):
        obs = frame[0].get("observation") or {}
        farms = obs.get("farms") or [{}, {}]
        f_h = farms[hero_idx] if len(farms) > hero_idx else {}
        f_o = farms[opp_idx] if len(farms) > opp_idx else {}
        
        m_h = float(f_h.get("money", 0) or 0)
        m_o = float(f_o.get("money", 0) or 0)
        q_h = len(f_h.get("unlocked_quadrants", []) or [])
        q_o = len(f_o.get("unlocked_quadrants", []) or [])
        w_h = len(f_h.get("hands", []) or [])
        w_o = len(f_o.get("hands", []) or [])
        
        # Count animals
        def count_anim(f):
            c = 0
            for r in (f.get("tiles") or []):
                for t in r:
                    if isinstance(t, dict) and t.get("animal") in ("COW", "SHEEP", "GOOSE"):
                        c += 1
            return c
            
        a_h = count_anim(f_h)
        a_o = count_anim(f_o)
        
        h_cash.append(m_h)
        o_cash.append(m_o)
        h_quads_list.append(q_h)
        o_quads_list.append(q_o)
        h_anim_list.append(a_h)
        o_anim_list.append(a_o)
        h_work_list.append(w_h)
        o_work_list.append(w_o)
        deltas.append(m_h - m_o)
        
    # Locate decisive divergence point
    # Find the earliest step where opponent gained a lead >= $3,000 and never gave it back
    div_step = len(steps) - 1
    for s in range(len(deltas)):
        if deltas[s] < -2500:
            # Check if hero ever reclaimed lead after step s
            if not any(d >= 0 for d in deltas[s:]):
                div_step = s
                break
                
    div_day = div_step // 24
    div_hour = div_step % 24
    
    # Categorize Temporal Phase
    if div_day <= 3:
        phase = "Day 0-3 (Opening Specialization)"
    elif div_day <= 7:
        phase = "Day 4-7 (Labor & Land Timing)"
    elif div_day <= 12:
        phase = "Day 8-12 (Livestock / Quadrant Scaling)"
    elif div_day <= 20:
        phase = "Day 13-20 (Compounding Engine Deficit)"
    else:
        phase = "Day 21-29 (Endgame & Liquidation)"
        
    # Characterize Opponent Strategy
    max_o_anim = max(o_anim_list) if o_anim_list else 0
    max_o_work = max(o_work_list) if o_work_list else 0
    max_o_quad = max(o_quads_list) if o_quads_list else 0
    
    # Find step opponent unlocked Q2
    o_q2_step = next((s for s, q in enumerate(o_quads_list) if q >= 2), None)
    h_q2_step = next((s for s, q in enumerate(h_quads_list) if q >= 2), None)
    
    if max_o_anim >= 6 and max_o_work >= 8:
        opp_archetype = "Aggressive Livestock Swarm"
    elif o_q2_step is not None and o_q2_step <= 144: # Day 6 or earlier
        opp_archetype = "Fast-Land Preemptor"
    elif max_o_anim <= 2:
        opp_archetype = "Crop Specialist"
    else:
        opp_archetype = "Balanced Hybrid"
        
    # Diagnosed Failure Mode & Prescribed Counter-Response
    if opp_archetype in ("Aggressive Livestock Swarm", "Fast-Land Preemptor"):
        if o_q2_step is not None and (h_q2_step is None or h_q2_step > o_q2_step + 48):
            failure_mode = "Land Expansion Lag (Opponent unlocked Q2 earlier and seized tile lead)"
            prescribed_response = "Preempt Q2 expansion when opp_quads >= 2 and cash >= $750"
        elif max_o_anim > max(h_anim_list) + 3:
            failure_mode = "Livestock Capacity Deficit (Opponent scaled 3+ more producing cows/sheep)"
            prescribed_response = "Reinvest surplus cash (>= $550) into Cow Matching on unlocked land"
        else:
            failure_mode = "Market Feed Exhaustion (Cash drained buying open-market feed)"
            prescribed_response = "Cap late feed buying and enforce self-sustaining wheat grain cycle"
    elif phase.startswith("Day 21"):
        failure_mode = "Liquidation Inventory Deadweight (Unsold commodities in shed at final steps)"
        prescribed_response = "Enforce full shed liquidation of Melon, Wheat, Wool, and Fertilizer at step >= 690"
    else:
        failure_mode = "Early Liquidity Depletion (Early cash starvation stalled worker wages)"
        prescribed_response = "Maintain strict minimum cash reserve of $180-$200 during early macro"
        
    return {
        "episode_id": eid,
        "seed": seed,
        "hero_name": h_name,
        "opp_name": o_name,
        "opp_elo": o_elo,
        "hero_wealth": h_rew,
        "opp_wealth": o_rew,
        "deficit": margin,
        "divergence_step": div_step,
        "divergence_day": div_day,
        "divergence_hour": div_hour,
        "temporal_phase": phase,
        "opp_archetype": opp_archetype,
        "hero_state_at_divergence": {
            "money": h_cash[div_step],
            "quads": h_quads_list[div_step],
            "animals": h_anim_list[div_step],
            "workers": h_work_list[div_step],
        },
        "opp_state_at_divergence": {
            "money": o_cash[div_step],
            "quads": o_quads_list[div_step],
            "animals": o_anim_list[div_step],
            "workers": o_work_list[div_step],
        },
        "failure_mode": failure_mode,
        "prescribed_counter_response": prescribed_response,
    }

def main():
    print("=" * 95)
    print("      BUILDING COMPREHENSIVE HARD-LOSS DATASET & TEMPORAL FAILURE MAP                   ")
    print("=" * 95)
    
    # Collect all available replay files
    replay_patterns = [
        r"D:\kaggriculture\reports\live_match_telemetry\episode-*-replay.json",
        r"D:\kaggriculture\reports\live_match_telemetry\downloaded_losses\*.json",
        r"D:\kaggriculture\topreply\loss\*.json",
    ]
    
    files = set()
    for p in replay_patterns:
        for f in glob.glob(p):
            files.add(f)
            
    print(f"Discovered {len(files)} candidate replay JSON files across telemetry directories.")
    
    losses = []
    for fpath in sorted(files):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            div = extract_divergence_from_replay(data)
            if div:
                losses.append(div)
        except Exception as e:
            continue
            
    print(f"Successfully processed {len(losses)} unique live match losses.")
    
    # Cluster statistics
    by_phase = defaultdict(list)
    by_archetype = defaultdict(list)
    for l in losses:
        by_phase[l["temporal_phase"]].append(l)
        by_archetype[l["opp_archetype"]].append(l)
        
    print("\n" + "-" * 95)
    print(f" {'TEMPORAL FAILURE CLUSTERING':^93} ")
    print("-" * 95)
    for ph, items in sorted(by_phase.items()):
        mean_def = sum(x["deficit"] for x in items) / len(items)
        print(f"  • {ph:<38} : {len(items):2d} losses (Mean Deficit: {mean_def:+,.0f})")
        
    print("\n" + "-" * 95)
    print(f" {'OPPONENT STRATEGY CLUSTERING':^93} ")
    print("-" * 95)
    for arch, items in sorted(by_archetype.items()):
        mean_def = sum(x["deficit"] for x in items) / len(items)
        print(f"  • {arch:<38} : {len(items):2d} losses (Mean Deficit: {mean_def:+,.0f})")
        
    print("\n" + "-" * 95)
    print(f" {'SAMPLE HARD-NEGATIVE REPAIR SIGNATURES':^93} ")
    print("-" * 95)
    for l in losses[:5]:
        print(f"  [Ep {l['episode_id']} vs {l['opp_name'][:14]} ({l['opp_elo']:.0f} Elo)] Deficit: {l['deficit']:+,.0f} at Day {l['divergence_day']}")
        print(f"    Failure    : {l['failure_mode']}")
        print(f"    Prescribed : {l['prescribed_counter_response']}\n")
        
    OUTPUT_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(losses, f, indent=2)
        
    print(f"Saved complete Hard-Loss Dataset ({len(losses)} cases) to: {OUTPUT_DATASET_PATH}")
    print("=" * 95)

if __name__ == "__main__":
    main()
