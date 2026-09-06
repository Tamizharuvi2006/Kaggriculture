import sys
sys.path.insert(0, r"D:\kaggriculture")

import kaggle_environments, json
from submission_rc2_terminal_horizon import agent as rc2_agent

seeds = [
    (105112452, 628719714, "$29,725 (Worst Low)"),
    (105105439, 334330253, "$38,075 (vs zZx Hee 90k)"),
    (105107201, 652661405, "$46,774 (vs 623 Elo 53k)"),
    (105116829, 264913612, "$57,833 (vs 596 Elo 68k)"),
    (105104584, 1064891062, "$73,237 (vs 760 Elo 113k)"),
]

for ep_id, seed, label in seeds:
    print("=" * 105)
    print(f"FORENSIC AUDIT: Episode {ep_id} | Seed {seed} | {label}")
    print("=" * 105)
    
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    daily_stats = []
    current_day = -1
    
    for step in range(720):
        if env.done: break
        obs = env.state[0].observation
        day = obs.day
        hour = obs.hour
        
        if day != current_day:
            current_day = day
            f0 = obs.farms[0]
            priv = env.state[0].observation.private
            shed = priv.get("shed", {})
            prices = obs.market.prices
            
            # Count assets
            crops = {}
            animals = {}
            unwatered = 0
            unfed = 0
            for row in f0.tiles:
                for tile in row:
                    if isinstance(tile, dict):
                        if tile.get("kind") == "PLANT":
                            c = tile.get("crop")
                            crops[c] = crops.get(c, 0) + 1
                            if not tile.get("watered_today", False) and day > 0:
                                unwatered += 1
                        elif tile.get("animal"):
                            a = tile.get("animal")
                            animals[a] = animals.get(a, 0) + 1
                            if not tile.get("fed_today", False) and day > 0:
                                unfed += 1
                                
            shed_units = sum(shed.values())
            crop_str = " ".join(f"{k}:{v}" for k, v in sorted(crops.items()))
            anim_str = " ".join(f"{k}:{v}" for k, v in sorted(animals.items()))
            
            daily_stats.append({
                "day": day,
                "money": f0.money,
                "crops": crop_str,
                "animals": anim_str,
                "shed_total": shed_units,
                "p_straw": prices.get("STRAWBERRY", 0),
                "p_melon": prices.get("MELON", 0),
                "p_milk": prices.get("MILK", 0),
                "p_wool": prices.get("WOOL", 0),
            })
            
        act0 = rc2_agent(obs)
        act1 = rc2_agent(env.state[1].observation)
        env.step([act0, act1])
        
    f0_final = env.state[0].observation.farms[0]
    print(f"{'Day':<4} | {'Money':>8} | {'Shed':>5} | {'Prices (Straw/Melon/Milk/Wool)':<32} | {'Crops & Animals':<40}")
    print("-" * 105)
    for s in daily_stats:
        if s["day"] in [0, 4, 8, 12, 16, 20, 24, 28, 29]:
            p_str = f"S:{s['p_straw']:>3} M:{s['p_melon']:>3} Mk:{s['p_milk']:>3} W:{s['p_wool']:>3}"
            ca_str = f"{s['crops']} | {s['animals']}"
            print(f"D{s['day']:<3} | ${s['money']:>7,.0f} | {s['shed_total']:>5} | {p_str:<32} | {ca_str}")
    print(f"FINAL MONETARY REWARD: ${f0_final.money:,.0f}")
    print()
