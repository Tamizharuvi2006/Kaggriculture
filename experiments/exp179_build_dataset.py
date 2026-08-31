"""
EXP179 — Step 1: Multi-Tier Authentic Replay Dataset Builder.
Crawls all JSON replays in the workspace, extracts state-action-reward tuples,
categorizes into Grandmaster, Competitive, and Population tiers, and outputs
structured NumPy arrays for hierarchical BC & Value Network pretraining.
"""

import json
import glob
import os
import time
import numpy as np

# Canonical constants
CROP_TYPES = ["CARROT", "TOMATO", "WHEAT", "STRAWBERRY", "MELON"]
ANIMAL_TYPES = ["COW", "SHEEP", "GOOSE"]
ALL_PRODUCTS = ["CARROT", "TOMATO", "WHEAT", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

def parse_replay_steps(replay_path):
    try:
        with open(replay_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        steps = data.get("steps", [])
        if not steps or len(steps) < 100:
            return None
        
        last_step = steps[-1]
        p0_rew = last_step[0].get("reward", 0.0) or 0.0
        p1_rew = last_step[1].get("reward", 0.0) or 0.0
        
        return {
            "path": replay_path,
            "steps": steps,
            "p0_reward": p0_rew,
            "p1_reward": p1_rew,
            "max_reward": max(p0_rew, p1_rew),
            "step_count": len(steps)
        }
    except Exception as e:
        return None

def extract_features_from_obs(obs, player_idx):
    farms = obs.get("farms", [{}, {}])
    if len(farms) <= player_idx:
        return None
    
    my_farm = farms[player_idx]
    opp_farm = farms[1 - player_idx]
    my_priv = obs.get("private", {})
    market_info = obs.get("market", {})
    
    # 1. Global Scalars (12 features)
    step = float(obs.get("step", 0))
    day = float(obs.get("day", 0))
    hour = float(obs.get("hour", 0))
    my_money = float(my_farm.get("money", 0.0))
    opp_money = float(opp_farm.get("money", 0.0))
    my_quads = float(len(my_farm.get("unlocked_quadrants", [])))
    opp_quads = float(len(opp_farm.get("unlocked_quadrants", [])))
    my_hands = float(len(my_farm.get("hands", [])))
    opp_hands = float(len(opp_farm.get("hands", [])))
    remaining_time = float(obs.get("remainingOverageTime", 60.0))
    
    global_vec = [
        step / 720.0,
        day / 30.0,
        hour / 24.0,
        np.log1p(max(0.0, my_money)) / 12.0,
        np.log1p(max(0.0, opp_money)) / 12.0,
        my_quads / 4.0,
        opp_quads / 4.0,
        my_hands / 16.0,
        opp_hands / 16.0,
        remaining_time / 60.0,
        float(player_idx),
        1.0 # bias
    ]
    
    # 2. Market Prices (9 features) & Shed Inventory (9 features)
    prices = market_info.get("prices", {})
    shed = my_priv.get("shed", {})
    price_vec = []
    shed_vec = []
    for prod in ALL_PRODUCTS:
        p_val = float(prices.get(prod, 10.0))
        price_vec.append(p_val / 300.0)
        s_val = float(shed.get(prod, 0))
        shed_vec.append(np.log1p(max(0.0, s_val)) / 6.0)
        
    # 3. Seed Inventory (5 features)
    seeds = my_priv.get("seeds", {})
    seed_vec = [float(seeds.get(c, 0)) / 20.0 for c in CROP_TYPES]
    
    # 4. Board Grid (10x10x6 spatial planes: Plant types, growth, watered, animal type, fed, manure)
    tiles = my_farm.get("tiles", [])
    grid = np.zeros((10, 10, 6), dtype=np.float32)
    
    for y in range(min(10, len(tiles))):
        for x in range(min(10, len(tiles[y]))):
            t = tiles[y][x]
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT":
                    crop_name = t.get("crop", "")
                    if crop_name in CROP_TYPES:
                        grid[y, x, 0] = (CROP_TYPES.index(crop_name) + 1.0) / 5.0
                    grid[y, x, 1] = float(t.get("yield_units", 0)) / 4.0
                    grid[y, x, 2] = 1.0 if t.get("watered_today", False) else 0.0
                elif k == "ANIMAL":
                    anim_name = t.get("animal", "")
                    if anim_name in ANIMAL_TYPES:
                        grid[y, x, 3] = (ANIMAL_TYPES.index(anim_name) + 1.0) / 3.0
                    grid[y, x, 4] = 1.0 if t.get("fed_today", False) else 0.0
                    grid[y, x, 5] = 1.0 if t.get("fertilizer_available", False) else 0.0
                    
    # Flatten features
    state_vector = np.concatenate([
        np.array(global_vec, dtype=np.float32),
        np.array(price_vec, dtype=np.float32),
        np.array(shed_vec, dtype=np.float32),
        np.array(seed_vec, dtype=np.float32),
        grid.flatten() # 10*10*6 = 600 floats
    ]) # Total dim: 12 + 9 + 9 + 5 + 600 = 635 floats
    
    return state_vector

def parse_macro_action(action_dict):
    """
    Macro category labels (0..15):
    0: PASS/HOLD
    1: HIRE_WORKER
    2: BUY_SEED_MELON
    3: BUY_SEED_STRAWBERRY
    4: BUY_SEED_WHEAT
    5: BUY_SEED_CARROT
    6: BUY_SEED_TOMATO
    7: BUY_ANIMAL_COW
    8: BUY_ANIMAL_SHEEP
    9: SELL_MELON
    10: SELL_STRAWBERRY
    11: SELL_FERTILIZER
    12: SELL_MILK
    13: SELL_WOOL
    14: SELL_WHEAT
    15: OTHER_MARKET
    """
    if not isinstance(action_dict, dict):
        return 0
    
    market_orders = action_dict.get("market", [])
    if not market_orders:
        return 0
    
    # Priority order for macro intent
    for order in market_orders:
        if not order:
            continue
        op = order[0]
        if op == "HIRE":
            return 1
        elif op == "BUY_SEED" and len(order) >= 2:
            c = order[1]
            if c == "MELON": return 2
            elif c == "STRAWBERRY": return 3
            elif c == "WHEAT": return 4
            elif c == "CARROT": return 5
            elif c == "TOMATO": return 6
        elif op == "BUY_ANIMAL" and len(order) >= 2:
            a = order[1]
            if a == "COW": return 7
            elif a == "SHEEP": return 8
        elif op == "SELL" and len(order) >= 2:
            p = order[1]
            if p == "MELON": return 9
            elif p == "STRAWBERRY": return 10
            elif p == "FERTILIZER": return 11
            elif p == "MILK": return 12
            elif p == "WOOL": return 13
            elif p == "WHEAT": return 14
            
    return 15

def main():
    print("=" * 80)
    print("EXP179 — MULTI-TIER AUTHENTIC REPLAY CORPUS DISCOVERY & EXTRACTION")
    print("=" * 80)
    
    t0 = time.time()
    all_files = glob.glob("D:/kaggriculture/**/*.json", recursive=True)
    replay_files = [f for f in all_files if "episode-" in f and f.endswith(".json")]
    
    print(f"Discovered {len(replay_files)} total episode JSON files on disk.")
    
    parsed_episodes = []
    for f in replay_files:
        p = parse_replay_steps(f)
        if p is not None:
            parsed_episodes.append(p)
            
    print(f"Successfully parsed {len(parsed_episodes)} valid full-match episodes.")
    
    # Tiers classification
    gm_episodes = [e for e in parsed_episodes if e["max_reward"] >= 120000.0]
    comp_episodes = [e for e in parsed_episodes if 70000.0 <= e["max_reward"] < 120000.0]
    pop_episodes = [e for e in parsed_episodes if e["max_reward"] < 70000.0]
    
    print(f"\nEpisode Tier Breakdown:")
    print(f"  * Tier 1 (Grandmaster >= $120k)  : {len(gm_episodes):4d} episodes")
    print(f"  * Tier 2 (Competitive $70k-$120k): {len(comp_episodes):4d} episodes")
    print(f"  * Tier 3 (Population < $70k)     : {len(pop_episodes):4d} episodes")
    
    # Extract State-Action-Reward tuples
    all_states = []
    all_macro_actions = []
    all_rewards = []
    all_tiers = []
    
    for tier_id, ep_list in [(1, gm_episodes), (2, comp_episodes), (3, pop_episodes)]:
        for ep in ep_list:
            steps = ep["steps"]
            p0_final_rew = ep["p0_reward"]
            p1_final_rew = ep["p1_reward"]
            
            for s in range(len(steps) - 1):
                st = steps[s]
                # Player 0
                obs0 = st[0].get("observation")
                act0 = steps[s+1][0].get("action") if s+1 < len(steps) else None
                if obs0 and act0:
                    vec0 = extract_features_from_obs(obs0, 0)
                    if vec0 is not None:
                        macro0 = parse_macro_action(act0)
                        all_states.append(vec0)
                        all_macro_actions.append(macro0)
                        all_rewards.append(p0_final_rew)
                        all_tiers.append(tier_id)
                        
                # Player 1
                obs1 = st[1].get("observation")
                act1 = steps[s+1][1].get("action") if s+1 < len(steps) else None
                if obs1 and act1:
                    vec1 = extract_features_from_obs(obs1, 1)
                    if vec1 is not None:
                        macro1 = parse_macro_action(act1)
                        all_states.append(vec1)
                        all_macro_actions.append(macro1)
                        all_rewards.append(p1_final_rew)
                        all_tiers.append(tier_id)
                        
    states_arr = np.array(all_states, dtype=np.float32)
    actions_arr = np.array(all_macro_actions, dtype=np.int64)
    rewards_arr = np.array(all_rewards, dtype=np.float32)
    tiers_arr = np.array(all_tiers, dtype=np.int32)
    
    os.makedirs("D:/kaggriculture/data", exist_ok=True)
    out_path = "D:/kaggriculture/data/exp179_dataset.npz"
    np.savez_compressed(
        out_path,
        states=states_arr,
        actions=actions_arr,
        rewards=rewards_arr,
        tiers=tiers_arr
    )
    
    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print("DATASET EXTRACTION COMPLETE:")
    print("=" * 80)
    print(f"  * Total State-Action Tuples Extracted: {len(states_arr):,}")
    print(f"  * Feature Vector Dimensions          : {states_arr.shape[1]}")
    print(f"  * Tier 1 (Grandmaster) Samples       : {np.sum(tiers_arr == 1):,}")
    print(f"  * Tier 2 (Competitive) Samples       : {np.sum(tiers_arr == 2):,}")
    print(f"  * Tier 3 (Population) Samples        : {np.sum(tiers_arr == 3):,}")
    print(f"  * Saved Compressed Dataset to        : {out_path} ({os.path.getsize(out_path) / (1024*1024):.2f} MB)")
    print(f"  * Extraction Time                    : {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()
