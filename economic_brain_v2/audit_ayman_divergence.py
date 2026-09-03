import sys
sys.path.insert(0, r"D:\kaggriculture")

import json, os, kaggle_environments
import economic_brain_v2.submission_adaptive_v2_economic as v2

replay_file = r"D:\kaggriculture\reports\live_match_telemetry\episode-104433117-replay.json"
with open(replay_file) as f: rep = json.load(f)

hero_seat = 0
opp_seat = 1
steps = rep["steps"]
opp_actions = [frame[opp_seat].get("action") for frame in steps[1:]]

# 1. Parse Live Replay (Old Bot) daily snapshot
live_daily = {}
for s, frame in enumerate(steps[1:]):
    day = s // 24
    hour = s % 24
    if hour == 0 or s == len(steps) - 2:
        obs = frame[hero_seat].get("observation", {}) or {}
        farm = (obs.get("farms", [{}, {}]) or [{}, {}])[hero_seat]
        mkt = obs.get("market", {}) or {}
        prices = mkt.get("prices", {}) or {}
        tiles = farm.get("tiles", []) or []
        
        crops = {}
        animals = {"COW": 0, "SHEEP": 0}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("crop"):
                        c = t.get("crop")
                        crops[c] = crops.get(c, 0) + 1
                    if t.get("animal") in animals:
                        animals[t.get("animal")] += 1
                        
        live_daily[day] = {
            "cash": farm.get("money", 0),
            "hands": len(farm.get("hands", []) or []),
            "quads": len(farm.get("unlocked_quadrants", ["NW"]) or ["NW"]),
            "cows": animals["COW"],
            "sheep": animals["SHEEP"],
            "crops": crops,
            "prices": prices,
        }

# 2. Simulate V2 Agent on the same seed and record daily snapshot
env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": rep["info"]["seed"]})
env.reset()

v2_daily = {}
for s in range(len(opp_actions)):
    if env.done: break
    obs = env.state[hero_seat].observation
    day = s // 24
    hour = s % 24
    
    if hour == 0 or s == len(opp_actions) - 1:
        farm = obs["farms"][hero_seat]
        mkt = obs.get("market", {}) or {}
        prices = mkt.get("prices", {}) or {}
        tiles = farm.get("tiles", []) or []
        
        crops = {}
        animals = {"COW": 0, "SHEEP": 0}
        for row in tiles:
            for t in row:
                if isinstance(t, dict):
                    if t.get("crop"):
                        c = t.get("crop")
                        crops[c] = crops.get(c, 0) + 1
                    if t.get("animal") in animals:
                        animals[t.get("animal")] += 1
                        
        v2_daily[day] = {
            "cash": farm.get("money", 0),
            "hands": len(farm.get("hands", []) or []),
            "quads": len(farm.get("unlocked_quadrants", ["NW"]) or ["NW"]),
            "cows": animals["COW"],
            "sheep": animals["SHEEP"],
            "crops": crops,
            "prices": prices,
        }
        
    act = v2.agent(obs)
    env.step([act, opp_actions[s]])

final_day = 29
if 29 not in v2_daily and v2_daily:
    v2_daily[29] = {
        "cash": env.state[hero_seat].reward,
        "hands": 0, "quads": 3, "cows": 0, "sheep": 0, "crops": {}, "prices": {}
    }

print("=" * 110)
print(f"   FORENSIC DIVERGENCE AUDIT: AYMAN ELAMIN (Episode 104433117)")
print(f"   Live Old Bot: ${rep['rewards'][hero_seat]:,.0f}  vs  V2 Economic Agent: ${env.state[hero_seat].reward:,.0f}  (Delta: ${env.state[hero_seat].reward - rep['rewards'][hero_seat]:+,.0f})")
print("=" * 110)
print(f"{'Day':<4} | {'Old Cash':<10} {'V2 Cash':<10} {'Delta':<10} | {'Old Quads/H/A':<14} {'V2 Quads/H/A':<14} | {'Old Crops':<22} | {'V2 Crops':<22}")
print("-" * 110)

key_days = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 29]
for d in key_days:
    o = live_daily.get(d, {})
    v = v2_daily.get(d, {})
    o_c = o.get("cash", 0)
    v_c = v.get("cash", 0)
    diff = v_c - o_c
    
    o_qha = f"Q{o.get('quads', 1)} H{o.get('hands', 0)} A{o.get('cows', 0)+o.get('sheep', 0)}"
    v_qha = f"Q{v.get('quads', 1)} H{v.get('hands', 0)} A{v.get('cows', 0)+v.get('sheep', 0)}"
    
    # Format crops compact
    def fmt_crops(c_dict):
        items = []
        for k in ["STRAWBERRY", "MELON", "WHEAT", "CARROT", "TOMATO"]:
            if k in c_dict and c_dict[k] > 0:
                short = "STR" if k == "STRAWBERRY" else "MEL" if k == "MELON" else "WHT" if k == "WHEAT" else "CAR" if k == "CARROT" else "TOM"
                items.append(f"{short}:{c_dict[k]}")
        return " ".join(items) if items else "-"
        
    o_crp = fmt_crops(o.get("crops", {}))
    v_crp = fmt_crops(v.get("crops", {}))
    
    print(f"D{d:02d} | ${o_c:>8,.0f} ${v_c:>8,.0f} ${diff:>+8,.0f} | {o_qha:<14} {v_qha:<14} | {o_crp:<22} | {v_crp:<22}")

print("=" * 110)
