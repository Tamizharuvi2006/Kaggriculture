import json
import kaggle_environments

replay_path = r"D:\kaggriculture\reports\live_match_telemetry\episode-104379472-replay.json"
with open(replay_path, "r", encoding="utf-8") as f:
    replay = json.load(f)

steps = replay.get("steps", [])
info = replay.get("info", {})
seed = info.get("seed")

arao_actions = [frame[0].get("action") for frame in steps[1:]]

import sys
sys.path.insert(0, r"D:\kaggriculture")
import submission_challenger_exp208_clean as challenger

def run_mod_agent(sheep_mult, hire_boost):
    # Test modified agent that boosts livestock investment
    def mod_agent(obs):
        act = challenger.agent(obs)
        if not isinstance(act, dict): return act
        
        step = int(obs.get("step") if obs.get("step") is not None else int(obs.get("day", 0))*24 + int(obs.get("hour", 0)))
        day = step // 24
        hour = step % 24
        
        farms = obs.get("farms", [{}, {}])
        own = farms[1] if len(farms) > 1 else {}
        money = float(own.get("money", 0))
        mkt_orders = list(act.get("market", []))
        
        # Day 4-10: Opportunistic Sheep scaling when money allows
        if 4 <= day <= 10 and hour == 4 and money >= 600.0:
            count = min(int(money // 600.0), sheep_mult)
            if count > 0 and not any(len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "SHEEP" for m in mkt_orders):
                mkt_orders.append(["BUY_ANIMAL", "SHEEP", count])
                
        # Proactive workforce scaling: Hire 1 worker if cash >= 300 and workers < 8
        hands = own.get("hands", [])
        if hire_boost and len(hands) < 8 and money >= 250.0 and hour == 2:
            if not any(len(m) >= 1 and m[0] == "HIRE" for m in mkt_orders):
                mkt_orders.append(["HIRE"])
                
        act["market"] = mkt_orders
        return act

    env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    
    challenger._V18_SELECTED_MARKET = {0: None, 1: None}
    challenger._V18_SELECTED_DAY = {0: None, 1: None}
    challenger._V18_SELECTED_BOARD = {0: None, 1: None}
    
    for s in range(len(arao_actions)):
        if env.done: break
        obs1 = env.state[1].observation
        act1 = mod_agent(obs1)
        act0 = arao_actions[s]
        env.step([act0, act1])
        
    return env.state[0].reward, env.state[1].reward

print(f"Base match: arao = $55,146 | Hero = $40,642")

for sm in [1, 2, 3]:
    for hb in [False, True]:
        r0, r1 = run_mod_agent(sm, hb)
        print(f"Config (Sheep={sm}, HireBoost={hb}): arao=${r0:,.0f} | Hero=${r1:,.0f} | Margin={r1 - r0:+,.0f}")
