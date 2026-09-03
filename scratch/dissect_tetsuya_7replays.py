import os
import json
import glob
from collections import defaultdict

def dissect_replay(path, category):
    filename = os.path.basename(path)
    print(f"\n{'='*80}")
    print(f"[{category.upper()}] Reading {filename}...")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    info = data.get("info", {})
    agents = info.get("Agents", [])
    rewards = data.get("rewards", [])
    seed = info.get("seed")
    eid = info.get("EpisodeId")
    
    p0_name = agents[0].get("Name", "P0") if len(agents) > 0 else "P0"
    p1_name = agents[1].get("Name", "P1") if len(agents) > 1 else "P1"
    
    # Identify tetsuya
    tetsuya_idx = 0 if "tetsuya" in p0_name.lower() else (1 if "tetsuya" in p1_name.lower() else None)
    if tetsuya_idx is None:
        # Check by team or display name
        tetsuya_idx = 0 # default
        
    opp_idx = 1 - tetsuya_idx
    tet_name = agents[tetsuya_idx].get("Name") if len(agents) > tetsuya_idx else f"Player {tetsuya_idx}"
    opp_name = agents[opp_idx].get("Name") if len(agents) > opp_idx else f"Player {opp_idx}"
    
    tet_reward = rewards[tetsuya_idx] if len(rewards) > tetsuya_idx else 0
    opp_reward = rewards[opp_idx] if len(rewards) > opp_idx else 0
    
    print(f"Episode: {eid} | Seed: {seed}")
    print(f"Hero: {tet_name} (${tet_reward:,.0f}) vs Opponent: {opp_name} (${opp_reward:,.0f}) | Margin: {tet_reward - opp_reward:+,.0f}")
    
    steps = data.get("steps", [])
    
    # Track land purchases
    tet_land_steps = []
    opp_land_steps = []
    
    # Track actions taken
    tet_action_counts = defaultdict(int)
    opp_action_counts = defaultdict(int)
    
    # Track Day 0 orders
    day0_tet_market = []
    day0_opp_market = []
    
    # Track progression across steps
    snapshots = [0, 24, 48, 72, 120, 168, 240, 480, 719] # Day 0, 1, 2, 3, 5, 7, 10, 20, 30
    progression = []
    
    for s_idx, step_frame in enumerate(steps):
        # In steps: step_frame[0] is player 0, step_frame[1] is player 1
        # Action taken at step s is stored in step_frame[p]["action"]
        if s_idx < len(steps) - 1:
            next_frame = steps[s_idx + 1]
            act_tet = next_frame[tetsuya_idx].get("action") or {}
            act_opp = next_frame[opp_idx].get("action") or {}
            
            mkt_tet = act_tet.get("market") or []
            mkt_opp = act_opp.get("market") or []
            
            if s_idx == 0:
                day0_tet_market = mkt_tet
                day0_opp_market = mkt_opp
                
            for order in mkt_tet:
                cmd = order[0] if isinstance(order, (list, tuple)) and order else str(order)
                tet_action_counts[cmd] += 1
                if cmd == "BUY_LAND":
                    day = s_idx // 24
                    hour = s_idx % 24
                    tet_land_steps.append((s_idx, day, hour, order))
                    
            for order in mkt_opp:
                cmd = order[0] if isinstance(order, (list, tuple)) and order else str(order)
                opp_action_counts[cmd] += 1
                if cmd == "BUY_LAND":
                    day = s_idx // 24
                    hour = s_idx % 24
                    opp_land_steps.append((s_idx, day, hour, order))
                    
        # Extract state snapshot
        if s_idx in snapshots:
            obs = step_frame[0].get("observation") or {}
            farms = obs.get("farms") or [{}, {}]
            day = s_idx // 24
            
            f_tet = farms[tetsuya_idx] if len(farms) > tetsuya_idx else {}
            f_opp = farms[opp_idx] if len(farms) > opp_idx else {}
            
            # Count animals & crops
            def parse_farm(f):
                money = f.get("money", 0)
                hands = len(f.get("hands", []))
                quads = len(f.get("unlocked_quadrants", []))
                tiles = f.get("tiles", [])
                cows, sheep, geese = 0, 0, 0
                plants = defaultdict(int)
                for r in tiles:
                    for t in r:
                        if not isinstance(t, dict): continue
                        anim = t.get("animal")
                        if anim == "COW": cows += 1
                        elif anim == "SHEEP": sheep += 1
                        elif anim == "GOOSE": geese += 1
                        if t.get("kind") == "PLANT":
                            crop = t.get("crop", "UNKNOWN")
                            plants[crop] += 1
                return money, hands, quads, cows, sheep, geese, dict(plants)
                
            p_tet = parse_farm(f_tet)
            p_opp = parse_farm(f_opp)
            progression.append((s_idx, day, p_tet, p_opp))
            
    print(f"\n  [Land Expansion Timestamps]")
    print(f"   {tet_name} Land Purchases: {tet_land_steps}")
    print(f"   {opp_name} Land Purchases: {opp_land_steps}")
    
    print(f"\n  [Day 0 Market Opening]")
    print(f"   {tet_name}: {day0_tet_market}")
    print(f"   {opp_name}: {day0_opp_market}")
    
    print(f"\n  [Lifetime Market Action Totals]")
    print(f"   {tet_name}: {dict(tet_action_counts)}")
    print(f"   {opp_name}: {dict(opp_action_counts)}")
    
    print(f"\n  [State Progression (Day, Money, Workers, Quads, Cows, Sheep, Plants)]")
    for s_idx, day, pt, po in progression:
        print(f"   Day {day:2d} (Step {s_idx:3d}) | {tet_name[:10]}: ${pt[0]:8,.0f}, {pt[1]:2d} W, {pt[2]} Q, {pt[3]} Cow, {pt[4]} Shp, Crops: {pt[6]}")
        print(f"   {' '*19} | {opp_name[:10]}: ${po[0]:8,.0f}, {po[1]:2d} W, {po[2]} Q, {po[3]} Cow, {po[4]} Shp, Crops: {po[6]}")
        
    return {
        "filename": filename,
        "category": category,
        "eid": eid,
        "seed": seed,
        "tet_name": tet_name,
        "opp_name": opp_name,
        "tet_reward": tet_reward,
        "opp_reward": opp_reward,
        "margin": tet_reward - opp_reward,
        "tet_lands": tet_land_steps,
        "opp_lands": opp_land_steps,
        "day0_tet": day0_tet_market,
        "progression": progression
    }

def main():
    win_files = sorted(glob.glob(r"D:\kaggriculture\topreply\win\*.json"))
    loss_files = sorted(glob.glob(r"D:\kaggriculture\topreply\loss\*.json"))
    
    print(f"Found {len(win_files)} win replays and {len(loss_files)} loss replays.")
    
    all_summaries = []
    for wf in win_files:
        s = dissect_replay(wf, "win")
        all_summaries.append(s)
        
    for lf in loss_files:
        s = dissect_replay(lf, "loss")
        all_summaries.append(s)
        
    # Aggregate insights
    print("\n" + "="*95)
    print("                      AGGREGATE ELITE ARCHETYPE ANALYSIS")
    print("="*95)
    print(f"{'Episode':<10} | {'Category':<6} | {'Tetsuya ($)':<12} | {'Opponent ($)':<12} | {'Margin':<10} | {'Land 2 (Day)':<12} | {'Land 3 (Day)':<12} | {'Land 4':<8}")
    print("-" * 95)
    for s in all_summaries:
        l2 = s["tet_lands"][0][1] if len(s["tet_lands"]) > 0 else "-"
        l3 = s["tet_lands"][1][1] if len(s["tet_lands"]) > 1 else "-"
        l4 = s["tet_lands"][2][1] if len(s["tet_lands"]) > 2 else "Never"
        print(f"{s['eid']:<10} | {s['category'].upper():<6} | ${s['tet_reward']:10,.0f} | ${s['opp_reward']:10,.0f} | {s['margin']:+9,.0f} | Day {str(l2):<8} | Day {str(l3):<8} | {str(l4):<8}")
        
    # Save full telemetry to json
    with open(r"D:\kaggriculture\reports\live_match_telemetry\tetsuya_7replays_forensics.json", "w") as f:
        # Convert non-serializable elements
        serializable = []
        for s in all_summaries:
            s_copy = dict(s)
            s_copy["progression"] = [
                {"step": p[0], "day": p[1], "tet": p[2], "opp": p[3]}
                for p in s["progression"]
            ]
            serializable.append(s_copy)
        json.dump(serializable, f, indent=2)
    print(f"\nSaved full telemetry to reports/live_match_telemetry/tetsuya_7replays_forensics.json")

if __name__ == "__main__":
    main()
