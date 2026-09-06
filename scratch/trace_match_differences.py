import os, sys, json
import kaggle_environments

MATCHES_TO_ANALYZE = [
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95773643\episode-95773643-replay.json", 0, "Match 19 (Ceiling)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95392785\episode-95392785-replay.json", 0, "Match 14 (Ceiling)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95622859\episode-95622859-replay.json", 0, "Match 17 (Floor Collapse)"),
    (r"D:\kaggriculture\reports\step5b\old_loss_gauntlet\raw_replays\95775674\episode-95775674-replay.json", 0, "Match 20 (Floor Collapse)"),
]

def trace_match(mod_name, replay_path, hero_seat, label):
    if mod_name in sys.modules: del sys.modules[mod_name]
    mod = __import__(mod_name)
    with open(replay_path, "r", encoding="utf-8") as f: rep = json.load(f)
    steps = rep["steps"]
    opp_seat = 1 - hero_seat
    opp_actions = [steps[s][opp_seat].get("action") for s in range(1, len(steps))]
    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps)-1, "seed": rep["info"]["seed"]})
    env.reset()
    
    daily_stats = []
    prev_day = -1
    for s in range(len(steps)-1):
        if env.done: break
        obs = env.state[hero_seat].observation
        day = obs["day"]
        act = mod.agent(obs)
        
        # Check animal purchases in action
        buys = [o for o in act.get("market", []) if o and o[0] == "BUY"]
        
        if day != prev_day:
            farm = obs["farms"][hero_seat]
            cows = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "ANIMAL" and t.get("animal") == "COW")
            sheep = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("kind") == "ANIMAL" and t.get("animal") == "SHEEP")
            wheat = int(obs["private"]["shed"].get("WHEAT", 0))
            money = int(farm["money"])
            strawberries = sum(1 for r in farm["tiles"] for t in r if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            daily_stats.append((day, money, cows, sheep, wheat, strawberries, buys))
            prev_day = day
            
        if hero_seat == 0:
            env.step([act, opp_actions[s]])
        else:
            env.step([opp_actions[s], act])
            
    final_score = int(env.state[hero_seat].observation["farms"][hero_seat]["money"])
    return final_score, daily_stats

if __name__ == "__main__":
    sys.path.insert(0, r"D:\kaggriculture")
    for rp, seat, label in MATCHES_TO_ANALYZE:
        print(f"\n==================== {label} ====================")
        s_rc12, stats_rc12 = trace_match("submission_rc12", rp, seat, label)
        s_rc6, stats_rc6 = trace_match("submission_rc6_d1", rp, seat, label)
        print(f"RC12 Score: ${s_rc12:,} | RC6_D1 Score: ${s_rc6:,}")
        print("Day | RC12: Money/Cows/Sheep/Wheat/Straw | RC6: Money/Cows/Sheep/Wheat/Straw | RC6 Buys")
        for d in range(min(len(stats_rc12), len(stats_rc6))):
            d12 = stats_rc12[d]
            d6 = stats_rc6[d]
            # Print if difference or key days
            if d12[2:6] != d6[2:6] or d in [10, 11, 12, 13, 14, 15, 20, 25, 29]:
                buys_str = str(d6[6]) if d6[6] else ""
                print(f"D{d:02d} | ${d12[1]:>6,} / {d12[2]}c {d12[3]}s / {d12[4]:>2d}w / {d12[5]:>2d}st | ${d6[1]:>6,} / {d6[2]}c {d6[3]}s / {d6[4]:>2d}w / {d6[5]:>2d}st | {buys_str}")
