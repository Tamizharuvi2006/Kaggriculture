"""
EXP179 — Worker Execution Dataset Extractor.
Extracts per-worker state features and target action labels (0..15)
from all authentic replays for training the Level 2/3 Spatial Motion Policy.
"""

import json
import glob
import os
import time
import numpy as np

CROP_TYPES = ["CARROT", "TOMATO", "WHEAT", "STRAWBERRY", "MELON"]

def parse_unit_action(act_item):
    if not act_item or not isinstance(act_item, list):
        return 0
    op = act_item[0]
    if op == "PASS": return 0
    elif op == "NORTH": return 1
    elif op == "SOUTH": return 2
    elif op == "EAST": return 3
    elif op == "WEST": return 4
    elif op in ["TILL", "DIG"]: return 5
    elif op == "PLANT":
        c = act_item[1] if len(act_item) > 1 else ""
        if c == "MELON": return 6
        elif c == "STRAWBERRY": return 7
        elif c == "WHEAT": return 8
        elif c == "CARROT": return 9
        elif c == "TOMATO": return 10
        return 6
    elif op == "WATER": return 11
    elif op == "HARVEST": return 12
    elif op in ["FEED", "CARE"]: return 13
    elif op == "COLLECT_FERTILIZER": return 14
    elif op in ["DROP", "PICKUP"]: return 15
    return 0

def extract_worker_sample(obs, player_idx, worker_pos, is_farmer, worker_inv, action_label):
    farms = obs.get("farms", [{}, {}])
    if len(farms) <= player_idx:
        return None
    my_farm = farms[player_idx]
    my_priv = obs.get("private", {})
    
    wx, wy = worker_pos
    if wx is None or wy is None:
        return None
        
    tiles = my_farm.get("tiles", [])
    if wy >= len(tiles) or wx >= len(tiles[wy]):
        return None
        
    curr_tile = tiles[wy][wx]
    
    # Feature representation (48 floats):
    # 1. Position & Role (4)
    # 2. Local Tile State (10)
    # 3. Worker Inventory (8)
    # 4. Global State & Seed Availability (16)
    # 5. Neighboring Tile Needs (10)
    
    vec = []
    # 1. Pos & Role
    vec.extend([wx / 10.0, wy / 10.0, 1.0 if is_farmer else 0.0, float(len(my_farm.get("hands", []))) / 16.0])
    
    # 2. Local tile state
    tile_kind = curr_tile.get("kind", "") if isinstance(curr_tile, dict) else ""
    is_plant = 1.0 if tile_kind == "PLANT" else 0.0
    is_animal = 1.0 if tile_kind == "ANIMAL" else 0.0
    is_empty = 1.0 if tile_kind == "EMPTY" or curr_tile is None else 0.0
    yield_units = float(curr_tile.get("yield_units", 0)) / 4.0 if is_plant else 0.0
    watered = 1.0 if (is_plant and curr_tile.get("watered_today", False)) else 0.0
    fed = 1.0 if (is_animal and curr_tile.get("fed_today", False)) else 0.0
    has_fert = 1.0 if (is_animal and curr_tile.get("fertilizer_available", False)) else 0.0
    crop_id = 0.0
    if is_plant:
        cname = curr_tile.get("crop", "")
        if cname in CROP_TYPES:
            crop_id = (CROP_TYPES.index(cname) + 1.0) / 5.0
            
    vec.extend([is_plant, is_animal, is_empty, yield_units, watered, fed, has_fert, crop_id, 0.0, 0.0])
    
    # 3. Worker Inventory
    inv = worker_inv if isinstance(worker_inv, dict) else {}
    held_wheat = float(inv.get("WHEAT", 0)) / 10.0
    held_melon = float(inv.get("MELON", 0)) / 10.0
    held_straw = float(inv.get("STRAWBERRY", 0)) / 10.0
    held_fert = float(inv.get("FERTILIZER", 0)) / 10.0
    total_held = float(sum(inv.values())) / 10.0
    vec.extend([held_wheat, held_melon, held_straw, held_fert, total_held, 0.0, 0.0, 0.0])
    
    # 4. Global State & Seeds
    step = float(obs.get("step", 0)) / 720.0
    day = float(obs.get("day", 0)) / 30.0
    hour = float(obs.get("hour", 0)) / 24.0
    money = np.log1p(max(0.0, float(my_farm.get("money", 0.0)))) / 12.0
    seeds = my_priv.get("seeds", {})
    melon_seeds = float(seeds.get("MELON", 0)) / 10.0
    straw_seeds = float(seeds.get("STRAWBERRY", 0)) / 10.0
    wheat_seeds = float(seeds.get("WHEAT", 0)) / 10.0
    vec.extend([step, day, hour, money, melon_seeds, straw_seeds, wheat_seeds, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    
    # 5. Local Board Summary (Unwatered count, mature count)
    unwatered_count = 0.0
    mature_count = 0.0
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                if t.get("yield_units", 0) > 0:
                    mature_count += 1.0
                elif not t.get("watered_today", False):
                    unwatered_count += 1.0
    vec.extend([unwatered_count / 50.0, mature_count / 50.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    
    return np.array(vec, dtype=np.float32), action_label

def main():
    print("=" * 80)
    print("EXP179 — WORKER MOTION & TASK EXECUTION DATASET EXTRACTION")
    print("=" * 80)
    
    t0 = time.time()
    all_files = glob.glob("D:/kaggriculture/**/*.json", recursive=True)
    replay_files = [f for f in all_files if "episode-" in f and f.endswith(".json")]
    
    worker_features = []
    worker_labels = []
    worker_tiers = []
    
    total_parsed = 0
    for f in replay_files:
        try:
            with open(f, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            steps = data.get("steps", [])
            if len(steps) < 100: continue
            
            p0_rew = steps[-1][0].get("reward", 0.0) or 0.0
            p1_rew = steps[-1][1].get("reward", 0.0) or 0.0
            max_r = max(p0_rew, p1_rew)
            tier = 1 if max_r >= 120000.0 else (2 if max_r >= 70000.0 else 3)
            
            for s in range(len(steps) - 1):
                st = steps[s]
                next_st = steps[s+1]
                
                # Player 0
                obs0 = st[0].get("observation")
                act0 = next_st[0].get("action")
                if obs0 and act0 and isinstance(act0, dict):
                    farm0 = obs0["farms"][0]
                    priv0 = obs0.get("private", {})
                    farmer_pos = farm0.get("farmer")
                    farmer_act = act0.get("farmer", ["PASS"])
                    farmer_inv = priv0.get("inventories", [{}])[0] if priv0.get("inventories") else {}
                    
                    if farmer_pos:
                        res = extract_worker_sample(obs0, 0, farmer_pos, True, farmer_inv, parse_unit_action(farmer_act))
                        if res:
                            worker_features.append(res[0])
                            worker_labels.append(res[1])
                            worker_tiers.append(tier)
                            
                    hands_list = farm0.get("hands", [])
                    hands_act = act0.get("hands", [])
                    for h_idx, h_pos in enumerate(hands_list):
                        h_act = hands_act[h_idx] if h_idx < len(hands_act) else ["PASS"]
                        h_inv = priv0.get("inventories", [{}])[h_idx+1] if len(priv0.get("inventories", [])) > h_idx+1 else {}
                        res = extract_worker_sample(obs0, 0, h_pos, False, h_inv, parse_unit_action(h_act))
                        if res:
                            worker_features.append(res[0])
                            worker_labels.append(res[1])
                            worker_tiers.append(tier)
                            
                # Player 1
                obs1 = st[1].get("observation")
                act1 = next_st[1].get("action")
                if obs1 and act1 and isinstance(act1, dict):
                    farm1 = obs1["farms"][1]
                    priv1 = obs1.get("private", {})
                    farmer_pos = farm1.get("farmer")
                    farmer_act = act1.get("farmer", ["PASS"])
                    farmer_inv = priv1.get("inventories", [{}])[0] if priv1.get("inventories") else {}
                    
                    if farmer_pos:
                        res = extract_worker_sample(obs1, 1, farmer_pos, True, farmer_inv, parse_unit_action(farmer_act))
                        if res:
                            worker_features.append(res[0])
                            worker_labels.append(res[1])
                            worker_tiers.append(tier)
                            
                    hands_list = farm1.get("hands", [])
                    hands_act = act1.get("hands", [])
                    for h_idx, h_pos in enumerate(hands_list):
                        h_act = hands_act[h_idx] if h_idx < len(hands_act) else ["PASS"]
                        h_inv = priv1.get("inventories", [{}])[h_idx+1] if len(priv1.get("inventories", [])) > h_idx+1 else {}
                        res = extract_worker_sample(obs1, 1, h_pos, False, h_inv, parse_unit_action(h_act))
                        if res:
                            worker_features.append(res[0])
                            worker_labels.append(res[1])
                            worker_tiers.append(tier)
            total_parsed += 1
        except Exception:
            continue
            
    X_worker = np.array(worker_features, dtype=np.float32)
    y_worker = np.array(worker_labels, dtype=np.int64)
    t_worker = np.array(worker_tiers, dtype=np.int32)
    
    out_path = "D:/kaggriculture/data/exp179_worker_dataset.npz"
    np.savez_compressed(
        out_path,
        features=X_worker,
        labels=y_worker,
        tiers=t_worker
    )
    
    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print("WORKER DATASET EXTRACTION COMPLETE:")
    print("=" * 80)
    print(f"  * Total Worker Step Samples Extracted: {len(X_worker):,}")
    print(f"  * Worker Feature Dimensions          : {X_worker.shape[1]}")
    print(f"  * Tier 1 (Grandmaster) Worker Steps  : {np.sum(t_worker == 1):,}")
    print(f"  * Tier 2 (Competitive) Worker Steps  : {np.sum(t_worker == 2):,}")
    print(f"  * Saved Compressed Dataset to        : {out_path} ({os.path.getsize(out_path)/(1024*1024):.2f} MB)")
    print(f"  * Extraction Time                    : {elapsed:.2f}s")

if __name__ == "__main__":
    main()
