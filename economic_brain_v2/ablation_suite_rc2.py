import sys
sys.path.insert(0, r"D:\kaggriculture")

import copy, json, os, time, math, kaggle_environments
import submission_rc1_ev_dispatcher as base_agent

replays = [
    ("episode-104475527-replay.json", 0, "RicardoLópez (1052 Elo)"),
    ("episode-104424149-replay.json", 0, "JZ (1000+ Elo)"),
    ("episode-104433117-replay.json", 0, "ayman elamin (1000+ Elo)"),
    ("episode-104388418-replay.json", 0, "Soumi Ghosh"),
    ("episode-104379472-replay.json", 0, "arao"),
]

def make_variant_agent(flags):
    """Dynamically configure RC1 Economic Brain with ablation flags."""
    orig_site_active = base_agent._animal_site_active
    orig_hire_target = base_agent._hire_target
    orig_crop_plan = base_agent._crop_plan
    orig_market_orders = base_agent._market_orders
    
    # Flag 1: Day-0 Livestock Blitz
    enable_day0_animals = flags.get("day0_animals", False)
    # Flag 2: Second Melon Cycle (Day 11-14)
    enable_second_melon = flags.get("second_melon", False)
    # Flag 3: High Strawberry + Terminal Wheat Conversion
    enable_high_strawberry = flags.get("high_strawberry", False)
    
    def custom_animal_site_active(pos, day, unlocked):
        x, y = pos
        if x < 5 and y < 5:
            return day >= (0 if enable_day0_animals else 4)
        if x >= 5 and y < 5:
            return "NE" in unlocked and day >= 7
        if x < 5 and y >= 5:
            return "SW" in unlocked and day >= 9
        return False

    def custom_hire_target(day):
        if enable_day0_animals and day <= 1:
            return 4 # 4 workers on day 0-1 to service early animals + crops
        if day <= 1: return 2
        if day <= 3: return 3
        if day <= 6: return 5
        if day <= 9: return 7
        if day <= 14: return 9
        if day <= 28: return 11
        return 6

    def custom_crop_plan(day):
        if day < 5:
            return base_agent.OPENING_CROP_PLAN
            
        prices = base_agent._LATEST_PRICES
        p_wheat = float(prices.get("WHEAT", 25.0) or 25.0)
        animal_plan = base_agent._animal_plan()
        num_animals = len(animal_plan)
        
        feed_wheat_plots = math.ceil(num_animals / 1.5)
        surplus_wheat_plots = 4 if p_wheat >= 28.0 else 0
        total_wheat_plots = max(4, feed_wheat_plots + surplus_wheat_plots)
        
        crop_scores = base_agent._evaluate_crop_scores(day, prices)
        cash_candidates = [c for c in ("STRAWBERRY", "MELON", "CARROT", "TOMATO") if crop_scores.get(c, -999.0) > 0]
        cash_candidates.sort(key=lambda c: crop_scores.get(c, -999.0), reverse=True)
        primary_cash_crop = cash_candidates[0] if cash_candidates else "CARROT"
        secondary_cash_crop = cash_candidates[1] if len(cash_candidates) > 1 else "CARROT"
        
        plan = {}
        # Melon logic
        if not enable_second_melon:
            plan = {pos: crop for pos, crop in base_agent.OPENING_CROP_PLAN.items() if crop == "MELON" and day <= 12}
        else:
            # Second melon wave: keep melons active through Day 22 for second cycle harvest!
            plan = {pos: crop for pos, crop in base_agent.OPENING_CROP_PLAN.items() if crop == "MELON" and day <= 22}

        candidates = [
            (x, y)
            for y in range(10)
            for x in range(10)
            if ((x < 5 and y < 5) or (x >= 5 and y < 5) or (x < 5 and y >= 5))
            and (x, y) not in animal_plan
            and (x, y) not in plan
        ]
        candidates.sort(key=lambda p: (abs(p[0] - 4.5) + abs(p[1] - 4.5), p[1], p[0]))
        
        # Terminal horizon conversion: on Day >= 22, long crops cannot finish; flip all free plots to 4-day Wheat!
        if enable_high_strawberry and day >= 22:
            for pos in candidates:
                plan[pos] = "WHEAT"
            return plan

        for pos in candidates[:total_wheat_plots]:
            plan[pos] = "WHEAT"
            
        rem = candidates[total_wheat_plots:]
        if enable_high_strawberry:
            # Saturate 100% of remaining plots with high-yield strawberry
            for pos in rem:
                plan[pos] = "STRAWBERRY"
        else:
            primary_quota = max(0, len(rem) - 6)
            for pos in rem[:primary_quota]:
                plan[pos] = primary_cash_crop
            for pos in rem[primary_quota:]:
                plan[pos] = secondary_cash_crop
                
        return plan

    def custom_market_orders(obs):
        day = int(base_agent._get(obs, "day", 0))
        hour = int(base_agent._get(obs, "hour", 0))
        player = int(base_agent._get(obs, "player", 0))
        farm = base_agent._get(obs, "farms", [])[player]
        budget = float(base_agent._get(farm, "money", 0))
        
        # Opening Day 0 Day-0 Animals intercept
        if enable_day0_animals and day == 0 and hour == 0:
            # Allocate capital: 4 hires + 2 Cows + 2 Sheep + 7 Melons + 7 Wheat
            orders = [
                ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
                ["BUY_ANIMAL", "COW", 2],
                ["BUY_ANIMAL", "SHEEP", 2],
                ["BUY_SEED", "MELON", 7],
                ["BUY_SEED", "WHEAT", 7],
            ]
            return orders
            
        return orig_market_orders(obs)

    # Monkey-patch base_agent directly
    base_agent._animal_site_active = custom_animal_site_active
    base_agent._hire_target = custom_hire_target
    base_agent._crop_plan = custom_crop_plan
    base_agent._market_orders = custom_market_orders
    
    def variant_agent(obs):
        if isinstance(obs, dict):
            base_agent._LATEST_PRICES = (obs.get("market", {}) or {}).get("prices", {}) or {}
        elif hasattr(obs, "market"):
            base_agent._LATEST_PRICES = getattr(obs.market, "prices", {}) or {}
        base_agent._observe_opponent(obs)
        unit_actions = base_agent._assign_actions(obs)
        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": custom_market_orders(obs),
        }
        
    def restore():
        base_agent._animal_site_active = orig_site_active
        base_agent._hire_target = orig_hire_target
        base_agent._crop_plan = orig_crop_plan
        base_agent._market_orders = orig_market_orders
        
    return variant_agent, restore

variants = [
    ("Variant A (RC1 Control)", {}),
    ("Variant B (Day-0 Animals)", {"day0_animals": True}),
    ("Variant C (Second Melon Wave)", {"second_melon": True}),
    ("Variant D (High Strawberry + Terminal Wheat)", {"high_strawberry": True}),
    ("Variant E (Combined All Three)", {"day0_animals": True, "second_melon": True, "high_strawberry": True}),
]

print("=" * 105)
print("     CONTROLLED ABLATION SUITE: 5 VARIANTS ACROSS 5 GAUNTLET SEEDS     ")
print("=" * 105)

results = {}

for v_name, flags in variants:
    print(f"\n--- Testing {v_name} ---")
    v_agent, restore = make_variant_agent(flags)
    variant_scores = []
    
    for r_name, cand_seat, opp_name in replays:
        path = os.path.join(r"D:\kaggriculture\reports\live_match_telemetry", r_name)
        with open(path) as f: rep = json.load(f)
        seed = rep["info"]["seed"]
        steps = rep["steps"]
        opp_actions = [frame[1 - cand_seat].get("action") for frame in steps[1:]]
        
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": len(steps), "seed": seed})
        env.reset()
        
        for s in range(len(opp_actions)):
            if env.done: break
            obs = env.state[cand_seat].observation
            act = v_agent(obs)
            env.step([act if cand_seat == 0 else opp_actions[s], opp_actions[s] if cand_seat == 0 else act])
            
        score = env.state[cand_seat].reward
        variant_scores.append(score)
        print(f"  {opp_name:<26}: ${score:,.0f}")
        sys.stdout.flush()
        
    restore()
        
    total_score = sum(variant_scores)
    avg_score = total_score / len(variant_scores)
    results[v_name] = {"total": total_score, "avg": avg_score, "scores": variant_scores}
    print(f"  => TOTAL: ${total_score:,.0f} | AVG: ${avg_score:,.0f}")

print("\n" + "=" * 105)
print("     ABLATION SUITE LEADERBOARD SUMMARY     ")
print("=" * 105)
control_total = results["Variant A (RC1 Control)"]["total"]
for v_name, res in results.items():
    diff = res["total"] - control_total
    print(f"  {v_name:<46} : ${res['total']:>8,.0f} (Avg: ${res['avg']:>6,.0f}) | Lift vs RC1: ${diff:+8,.0f}")
print("=" * 105)
