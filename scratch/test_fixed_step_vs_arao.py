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

# Fix _base_agent and agent to correctly read step
def _get_step(obs):
    s = obs.get("step") if isinstance(obs, dict) else getattr(obs, "step", None)
    if s is not None:
        return int(s)
    d = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
    h = int(obs.get("hour", 0) if isinstance(obs, dict) else getattr(obs, "hour", 0) or 0)
    return d * 24 + h

challenger._get_step = _get_step

# Override _base_agent
def clean_base_agent_fixed(obs):
    try:
        step = min(max(0, _get_step(obs)), 719)
        raw = challenger._v18_closed_loop_action(obs, step)
        overlaid = challenger._copy_action(raw)
        return challenger._apply_fixed_board_adaptation(obs, overlaid)
    except Exception as e:
        return {"farmer": ["PASS"], "hands": [], "market": []}

challenger._base_agent = clean_base_agent_fixed

# Override agent
def clean_agent_fixed(obs, configuration=None):
    try:
        step = _get_step(obs)
        player = int(obs.get("player", 0) if isinstance(obs, dict) else getattr(obs, "player", 0) or 0)
        day = int(obs.get("day", step // 24) if isinstance(obs, dict) else getattr(obs, "day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) if isinstance(obs, dict) else getattr(obs, "hour", step % 24) or 0)
        
        farms = obs.get("farms") or [] if isinstance(obs, dict) else getattr(obs, "farms", []) or []
        own_farm = farms[player] if len(farms) > player else {}
        money = float(own_farm.get("money", 0.0) or 0.0)
        priv = obs.get("private") or {} if isinstance(obs, dict) else getattr(obs, "private", {}) or {}
        shed = priv.get("shed") or {}
        milk_in_shed = int(shed.get("MILK", 0) or 0)
        fert_in_shed = int(shed.get("FERTILIZER", 0) or 0)
        straw_in_shed = int(shed.get("STRAWBERRY", 0) or 0)
        wool_in_shed = int(shed.get("WOOL", 0) or 0)
        melon_in_shed = int(shed.get("MELON", 0) or 0)
        unlocked = own_farm.get("unlocked_quadrants") or ["NW"]
        hands = own_farm.get("hands") or []

        mkt = obs.get("market") or {} if isinstance(obs, dict) else getattr(obs, "market", {}) or {}
        prices = mkt.get("prices") or {}
        p_fert = float(prices.get("FERTILIZER", 80.0) or 80.0)
        p_wheat = float(prices.get("WHEAT", 30.0) or 30.0)
        p_milk = float(prices.get("MILK", 160.0) or 160.0)
        p_wool = float(prices.get("WOOL", 180.0) or 180.0)
        p_straw = float(prices.get("STRAWBERRY", 120.0) or 120.0)

        act = challenger._base_agent(obs)
        if not isinstance(act, dict):
            return act

        market_orders = list(act.get("market") or [])

        # 1. End of game clearance (step >= 690, Day 29+): Force sell everything
        if step >= 690:
            clean_orders = []
            if straw_in_shed > 0: clean_orders.append(["SELL", "STRAWBERRY", straw_in_shed])
            if milk_in_shed > 0: clean_orders.append(["SELL", "MILK", milk_in_shed])
            if fert_in_shed > 0: clean_orders.append(["SELL", "FERTILIZER", fert_in_shed])
            if wool_in_shed > 0: clean_orders.append(["SELL", "WOOL", wool_in_shed])
            if melon_in_shed > 0: clean_orders.append(["SELL", "MELON", melon_in_shed])
            if clean_orders:
                act["market"] = clean_orders
            return act

        # 2. Continuous 3-Hour Fertilizer Micro-Liquidity Recycling
        if day >= 3 and hour % 3 == 0 and p_fert >= 48.0:
            if fert_in_shed >= 2 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "SELL" and m[1] == "FERTILIZER" for m in market_orders):
                market_orders.append(["SELL", "FERTILIZER", fert_in_shed])

        # 3. Gated Elite Transitions:
        if day == 2 and hour == 2:
            if p_fert >= 48.0 and p_wheat <= 38.0 and money >= 150.0:
                if money >= 120.0 and not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_PRODUCT" and m[1] == "WHEAT" for m in market_orders):
                    market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                if money >= 40.0 and len(hands) == 0 and not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "HIRE" for m in market_orders):
                    market_orders.append(["HIRE"])

        if day == 6 and hour == 16 and money >= 850.0 and p_milk >= 130.0:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "COW" for m in market_orders):
                market_orders.append(["BUY_ANIMAL", "COW", 1])

        if day == 7 and hour == 2 and money >= 500.0 and len(unlocked) < 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                market_orders.append(["BUY_LAND"])

        if day == 8 and hour == 4:
            market_orders = [m for m in market_orders if not (isinstance(m, (list, tuple)) and len(m) >= 2 and m[0] == "BUY_ANIMAL" and m[1] == "SHEEP")]
            if p_wool >= 130.0 and money >= 2400.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 4])
            elif money >= 1200.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
            elif money >= 600.0:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 1])

        if (day == 11 or day == 12) and hour == 2 and money >= 810.0 and len(unlocked) == 2:
            if not any(isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND" for m in market_orders):
                market_orders.append(["BUY_LAND"])

        final_orders = []
        for m in market_orders:
            if isinstance(m, (list, tuple)) and len(m) >= 1 and m[0] == "BUY_LAND":
                if len(unlocked) >= 3:
                    continue
            final_orders.append(m)

        act["market"] = final_orders
        return act
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}

env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
env.reset()

challenger._V18_SELECTED_MARKET = {0: None, 1: None}
challenger._V18_SELECTED_DAY = {0: None, 1: None}
challenger._V18_SELECTED_BOARD = {0: None, 1: None}

for s in range(len(arao_actions)):
    if env.done:
        break
    obs1 = env.state[1].observation
    act1 = clean_agent_fixed(obs1)
    act0 = arao_actions[s]
    env.step([act0, act1])

reward_arao = env.state[0].reward
reward_hero = env.state[1].reward

print(f"=========================================================================================")
print(f"     AFTER STEP FIX: REPLAY MATCH ON SEED {seed}                                        ")
print(f"=========================================================================================")
print(f"Original Live Match: arao = $55,146 | Hero = $40,642 (Loss by -$14,504)")
print(f"Fixed Agent Result : arao = ${reward_arao:,.0f} | Hero = ${reward_hero:,.0f} (Margin: {reward_hero - reward_arao:+,.0f})")
